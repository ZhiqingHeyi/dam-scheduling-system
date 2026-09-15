# -*- coding: utf-8 -*-
"""
本地运行一次「真实后端排仓管线」，把真实 visualization_data 导出为前端演示数据。

用途：Vercel 只托管静态前端，这里在本地算好真实结果，落地成
      frontend/public/sample_visualization.json / sample_scheduling.json，
      使演示页的排仓结果与可视化与本地完整程序完全一致。
"""
import os, sys, json, asyncio, shutil

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

import pandas as pd

SRC_UPLOAD = os.path.join(BASE_DIR, 'uploads')
TMP_UPLOAD = os.path.join(BASE_DIR, '_tmp_uploads')


def prepare_uploads():
    """把中文列名的原始 Excel 转成后端管线需要的英文列名，输出到临时目录。"""
    os.makedirs(TMP_UPLOAD, exist_ok=True)

    base = pd.read_excel(os.path.join(SRC_UPLOAD, 'BaselineSchedule.xlsx'))
    base = base.rename(columns={
        '坝段号': 'DamID', '层号': 'LayerID',
        '开始时间': 'PlanStart', '结束时间': 'PlanEnd',
        '浇筑高程': 'TopElev',
    })
    base = base.dropna(subset=['DamID', 'LayerID']).reset_index(drop=True)
    base['DamID'] = base['DamID'].astype(int)
    base['LayerID'] = base['LayerID'].astype(int)
    base.to_excel(os.path.join(TMP_UPLOAD, 'BaselineSchedule.xlsx'), index=False)

    top_map = dict(zip(zip(base['DamID'], base['LayerID']), base['TopElev']))

    act = pd.read_excel(os.path.join(SRC_UPLOAD, 'ActualDone.xlsx'))
    act = act.rename(columns={
        '坝段号': 'DamID', '层号': 'LayerID',
        '开始时间': 'ActualStart', '结束时间': 'ActualEnd',
    })
    act = act.dropna(subset=['DamID', 'LayerID']).reset_index(drop=True)
    act['DamID'] = act['DamID'].astype(int)
    act['LayerID'] = act['LayerID'].astype(int)
    act['ActualTopElev'] = [
        float(top_map.get((d, l))) if pd.notna(top_map.get((d, l))) else None
        for d, l in zip(act['DamID'], act['LayerID'])
    ]
    act.to_excel(os.path.join(TMP_UPLOAD, 'ActualDone.xlsx'), index=False)

    for f in ('WarehouseData_filled.xlsx', 'DamElevation.xlsx', 'AHPScores.xlsx'):
        src = os.path.join(SRC_UPLOAD, f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(TMP_UPLOAD, f))

    print(f'Baseline: {len(base)} 行, ActualDone: {len(act)} 行')
    return base, act


def sanitize(obj):
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, float):
        import math
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


async def main():
    prepare_uploads()

    import config
    config.settings.UPLOAD_DIR = TMP_UPLOAD
    config.settings.OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

    from api.scheduling import run_scheduling_pipeline, SchedulingRequest

    req = SchedulingRequest()
    result = await run_scheduling_pipeline(req, None)

    viz = result.get('visualization_data', {})
    print('=== 真实后端可视化结果 ===')
    for key in ('fixedWindow', 'nextMonthWindow', 'rollingWindow'):
        w = viz.get(key, {})
        wh = w.get('warehouses', [])
        seg = {}
        for x in wh:
            seg[x.get('segment')] = seg.get(x.get('segment'), 0) + 1
        print(f"{key}: {w.get('windowStart')} ~ {w.get('windowEnd')} | "
              f"totalCount={w.get('totalCount')} | dams={len(w.get('dams', []))} | "
              f"warehouses={len(wh)} {seg}")
    print('consistencyCheck:', viz.get('consistencyCheck'))
    print('debug_info:', result.get('debug_info'))

    out_dir = os.path.join(BASE_DIR, '..', 'frontend', 'public')
    os.makedirs(out_dir, exist_ok=True)

    viz_path = os.path.join(out_dir, 'sample_visualization.json')
    with open(viz_path, 'w', encoding='utf-8') as f:
        json.dump(sanitize(viz), f, ensure_ascii=False, indent=1, allow_nan=False)
    print('WROTE:', viz_path, os.path.getsize(viz_path) // 1024, 'KB')

    out = {
        'success': True,
        'message': result.get('message', '排仓计算完成'),
        'final_mode': result.get('final_mode', ''),
        'final_end_date': result.get('final_end_date', ''),
        'used_compression': result.get('used_compression', False),
        'visualization_data': viz,
        'debug_info': result.get('debug_info', {}),
        'schedule_data': [],
        'sorted_report': [],
    }
    sched_path = os.path.join(out_dir, 'sample_scheduling.json')
    with open(sched_path, 'w', encoding='utf-8') as f:
        json.dump(sanitize(out), f, ensure_ascii=False, indent=1, allow_nan=False)
    print('WROTE:', sched_path, os.path.getsize(sched_path) // 1024, 'KB')


if __name__ == '__main__':
    asyncio.run(main())
