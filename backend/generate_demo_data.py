# -*- coding: utf-8 -*-
"""
用真实 Excel 数据生成完整的可视化演示数据（35坝段 1700+仓面），
供 Vercel 纯前端展示使用（与本地部署结果一致）。
"""
import os, json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'Run_20260807_163323')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')


def norm(x):
    if pd.isna(x):
        return None
    return x


def to_float(x):
    if x is None or pd.isna(x):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace(',', '').replace('，', '').replace(' ', '').replace('\u3000', '')
    try:
        return float(s)
    except Exception:
        return None


def safe_date(x):
    if x is None or pd.isna(x):
        return None
    if isinstance(x, pd.Timestamp):
        return x.strftime('%Y-%m-%d')
    s = str(x).strip()
    for fmt in ('%Y/%m/%d', '%Y-%m-%d'):
        try:
            return pd.Timestamp(s).strftime('%Y-%m-%d')
        except Exception:
            continue
    return s


def main():
    # ---------- 1. B段：完整排仓计划（1767仓面，35坝段） ----------
    plan = pd.read_excel(os.path.join(OUTPUT_DIR, '完整排仓计划.xlsx'))
    b_warehouses = []
    for _, r in plan.iterrows():
        dam = int(r['坝段号'])
        layer = int(r['仓号'])
        top = float(r['仓顶高程(m)'])
        b_warehouses.append({
            'warehouseId': f'{dam}-{layer}',
            'damId': dam,
            'layerId': layer,
            'bottomElev': top - 3,
            'topElev': top,
            'segment': 'B',
            'startTime': safe_date(r['新排仓开始时间']) or safe_date(r['计划开始时间']),
        })

    # ---------- 2. A段：已浇筑（ActualDone） ----------
    base = pd.read_excel(os.path.join(UPLOAD_DIR, 'BaselineSchedule.xlsx'))
    elev_map = {}
    for _, r in base.iterrows():
        d = norm(r.get('坝段号'))
        l = norm(r.get('层号'))
        e = to_float(norm(r.get('浇筑高程')))
        if d is not None and l is not None and e is not None:
            elev_map[(int(d), int(l))] = float(e)

    done = pd.read_excel(os.path.join(UPLOAD_DIR, 'ActualDone.xlsx'))
    a_warehouses = []
    for _, r in done.iterrows():
        d = norm(r.get('坝段号'))
        l = norm(r.get('层号'))
        if d is None or l is None:
            continue
        dam, layer = int(d), int(l)
        top = elev_map.get((dam, layer), 750.0 + layer * 3)
        a_warehouses.append({
            'warehouseId': f'{dam}-{layer}',
            'damId': dam,
            'layerId': layer,
            'bottomElev': top - 3,
            'topElev': top,
            'segment': 'A',
            'startTime': safe_date(r.get('开始时间')),
        })

    print('A段(已浇筑):', len(a_warehouses), ' B段(计划):', len(b_warehouses))

    # ---------- 3. 排序 B段（按开始时间） ----------
    b_sorted = sorted(b_warehouses, key=lambda w: w['startTime'] or '9999')
    n = len(b_sorted)

    all_a = sorted(a_warehouses, key=lambda w: w['damId'])

    def make_window(b_list, label):
        w_list = all_a + b_list
        start_times = [w['startTime'] for w in w_list if w['startTime']]
        start_times.sort()
        window_start = start_times[0] if start_times else None
        window_end = start_times[-1] if start_times else None
        seg = {'A': 0, 'B': 0, 'C': 0}
        for w in w_list:
            s = w['segment']
            seg[s] = seg.get(s, 0) + 1
        dams = sorted(set(w['damId'] for w in w_list))
        return {
            'windowStart': window_start,
            'windowEnd': window_end,
            'totalCount': len(w_list),
            'segmentCounts': seg,
            'dams': dams,
            'warehouses': w_list,
            '_label': label,
        }

    # 三个窗口均展示完整大坝（全部仓面），保证每个 tab 都能看到完整坝体
    fixed_win = make_window(b_sorted, '全部')
    next_win = make_window(b_sorted, '全部')
    rolling_win = make_window(b_sorted, '全部')

    dams_all = sorted(set(w['damId'] for w in (all_a + b_warehouses)))
    print('坝段数:', len(dams_all), '范围:', dams_all[0], '-', dams_all[-1])

    visualization_data = {
        'available': True,
        'finalMode': '正常模式',
        'scheduleStart': fixed_win['windowStart'],
        'scheduleEnd': rolling_win['windowEnd'],
        'fixedWindow': {k: v for k, v in fixed_win.items() if k != '_label'},
        'nextMonthWindow': {k: v for k, v in next_win.items() if k != '_label'},
        'rollingWindow': {k: v for k, v in rolling_win.items() if k != '_label'},
        'consistencyCheck': {
            'fixedCount': fixed_win['totalCount'],
            'nextMonthCount': next_win['totalCount'],
            'rollingCount': rolling_win['totalCount'],
            'totalWarehouses': len(all_a) + n,
        }
    }

    # ---------- 4. 写入 sample_visualization.json ----------
    viz_path = os.path.join(BASE_DIR, '..', 'frontend', 'public', 'sample_visualization.json')
    with open(viz_path, 'w', encoding='utf-8') as f:
        json.dump(visualization_data, f, ensure_ascii=False, indent=1, default=str)
    print('WROTE:', viz_path, 'size:', os.path.getsize(viz_path) // 1024, 'KB')

    # ---------- 5. 写入 sample_scheduling.json（含 visualization_data） ----------
    last_end = sorted([w['startTime'] for w in b_warehouses if w['startTime']])
    final_end = last_end[-1] if last_end else None

    output = {
        'success': True,
        'message': '排仓计算完成（一体化演示数据）',
        'final_mode': '正常模式',
        'final_end_date': final_end,
        'used_compression': False,
        'visualization_data': visualization_data,
        'debug_info': {
            'n_warehouses': len(b_warehouses),
            'n_a': len(a_warehouses),
            'n_b': len(b_warehouses),
            'n_c': 0,
            'final_mode': '正常模式',
            'is_deadline_satisfied': True,
            'overdue_days': 0,
            'used_compression': False,
            'cr': 0.05,
        },
        'schedule_data': [],
        'sorted_report': [],
    }

    sched_path = os.path.join(BASE_DIR, '..', 'frontend', 'public', 'sample_scheduling.json')
    with open(sched_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=1, default=str)
    print('WROTE:', sched_path, 'size:', os.path.getsize(sched_path) // 1024, 'KB')


if __name__ == '__main__':
    main()
