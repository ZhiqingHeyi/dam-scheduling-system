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


def sanitize(obj):
    """将 NaN/Inf 等 JSON 非法值统一转为可序列化的值，确保输出为合法 JSON。"""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, float):
        if pd.isna(obj):
            return None
        import math
        if math.isinf(obj):
            return None
    return obj


# ---------------- 复刻后端真实窗口逻辑 ----------------

def get_fixed_monthly_window(ref_date=None):
    """固定周期窗口：按月 26 日~次月 25 日分界，与后端 scheduling_algorithm 保持一致。"""
    if ref_date is not None:
        today = pd.Timestamp(ref_date)
    else:
        today = pd.Timestamp.now()
    d = today.day
    y = today.year
    m = today.month

    if d >= 26:
        win_start = today.replace(day=26)
        win_end = (win_start + pd.DateOffset(months=1)).replace(day=25)
    else:
        this_month_start = today.replace(day=1)
        prev_month = this_month_start - pd.DateOffset(months=1)
        win_start = prev_month.replace(day=26)
        win_end = today.replace(day=25)

    return win_start, win_end


def get_next_fixed_monthly_window(ref_date=None):
    current_start, current_end = get_fixed_monthly_window(ref_date)
    next_start = current_end + pd.Timedelta(days=1)
    next_end = next_start + (current_end - current_start)
    return next_start, next_end


def get_rolling_window(b_start: pd.Timestamp):
    """滚动周期窗口：B 段最早开始日起，到下个月同日的前一天。"""
    rolling_start = pd.Timestamp(b_start).normalize()
    y, m, d = rolling_start.year, rolling_start.month, rolling_start.day

    next_y, next_m = y, m + 1
    if next_m > 12:
        next_m = 1
        next_y = y + 1

    import calendar
    last_day_next_month = calendar.monthrange(next_y, next_m)[1]
    same_day_next_month = min(d, last_day_next_month)
    next_month_same_day = pd.Timestamp(year=next_y, month=next_m, day=same_day_next_month)
    rolling_end = (next_month_same_day - pd.Timedelta(days=1)).normalize()
    return rolling_start, rolling_end


def overlap(win_start, win_end):
    return lambda s, e: (s and pd.Timestamp(s) <= win_end and e and pd.Timestamp(e) >= win_start)


def main():
    # ---------- 1. B段：完整排仓计划（1767仓面，35坝段） ----------
    plan = pd.read_excel(os.path.join(OUTPUT_DIR, '完整排仓计划.xlsx'))
    b_warehouses = []
    for _, r in plan.iterrows():
        dam = int(r['坝段号'])
        layer = int(r['仓号'])
        top_raw = to_float(norm(r.get('仓顶高程(m)')))
        if top_raw is None:
            top_raw = 750.0 + layer * 3.0
        top = float(top_raw)
        b_warehouses.append({
            'warehouseId': f'{dam}-{layer}',
            'damId': dam,
            'layerId': layer,
            'bottomElev': top - 3,
            'topElev': top,
            'segment': 'B',
            'startTime': safe_date(r['新排仓开始时间']) or safe_date(r['计划开始时间']),
            'endTime': safe_date(r['新排仓结束时间']) or safe_date(r['计划结束时间']),
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

    # ---------- 3.1 按真实后端逻辑划分三个时间窗口 ----------
    now = pd.Timestamp.now()
    fixed_window = get_fixed_monthly_window(now)
    next_window = get_next_fixed_monthly_window(now)
    b_first_start = pd.Timestamp(min((w['startTime'] for w in b_sorted if w['startTime']))).normalize()
    rolling_window = get_rolling_window(b_first_start)

    print('窗口划分:')
    print('  固定周期:', fixed_window[0].date(), '-', fixed_window[1].date())
    print('  下月度:  ', next_window[0].date(), '-', next_window[1].date())
    print('  滚动周期:', rolling_window[0].date(), '-', rolling_window[1].date())


    def build_window(b_list, win_start, win_end):
        """窗口 = 该窗口内重叠的计划B段仓面 + 全部已浇筑A段背景（.复刻 prepare_chart_data_with_poured）。"""
        win_start = pd.Timestamp(win_start)
        win_end = pd.Timestamp(win_end)

        # 窗口内计划仓面（按 FinalStart~FinalEnd 与窗口有重叠）
        in_win = [
            w for w in b_list
            if w['startTime'] and w['endTime']
            and pd.Timestamp(w['startTime']) <= win_end
            and pd.Timestamp(w['endTime']) >= win_start
        ]
        in_win = sorted(in_win, key=lambda w: (pd.Timestamp(w['startTime']) if w['startTime'] else pd.Timestamp.max))
        for i, w in enumerate(in_win):
            w['displayOrder'] = i + 1

        win_ids = {w['warehouseId'] for w in in_win}
        planned_dams = {w['damId'] for w in in_win}
        poured_dams = {w['damId'] for w in all_a}
        all_dams = sorted(planned_dams | poured_dams)

        # 已浇筑A段背景：凡 damId 在 all_dams 且不在窗口计划内均保留（完整大坝下半部分）
        poured = []
        for w in all_a:
            if w['warehouseId'] in win_ids:
                continue
            if w['damId'] not in all_dams:
                continue
            poured.append({**w, 'displayOrder': 0})
        poured.sort(key=lambda w: w['damId'])

        w_list = poured + in_win
        seg = {'A': 0, 'B': 0, 'C': 0}
        for w in w_list:
            seg[w['segment']] = seg.get(w['segment'], 0) + 1

        return {
            'windowStart': str(win_start.date()),
            'windowEnd': str(win_end.date()),
            'totalCount': len(in_win),
            'segmentCounts': seg,
            'dams': all_dams,
            'warehouses': w_list,
        }


    fixed_win = build_window(b_sorted, *fixed_window)
    next_win = build_window(b_sorted, *next_window)
    rolling_win = build_window(b_sorted, *rolling_window)

    dams_all = sorted(set(w['damId'] for w in (all_a + b_warehouses)))
    print('坝段数:', len(dams_all), '范围:', dams_all[0], '-', dams_all[-1])
    print('固定周期计划仓面:', fixed_win['totalCount'], ' 下月度:', next_win['totalCount'], ' 滚动:', rolling_win['totalCount'])

    visualization_data = {
        'available': True,
        'finalMode': '正常模式',
        'scheduleStart': str(pd.Timestamp(min(w['startTime'] for w in b_sorted if w['startTime'])).date()),
        'scheduleEnd': str(pd.Timestamp(max(w['startTime'] for w in b_sorted if w['startTime'])).date()),
        'fixedWindow': fixed_win,
        'nextMonthWindow': next_win,
        'rollingWindow': rolling_win,
        'consistencyCheck': {
            'fixedWindowRange': f"{fixed_window[0].strftime('%Y%m%d')}-{fixed_window[1].strftime('%Y%m%d')}",
            'nextMonthWindowRange': f"{next_window[0].strftime('%Y%m%d')}-{next_window[1].strftime('%Y%m%d')}",
            'rollingWindowRange': f"{rolling_window[0].strftime('%Y%m%d')}-{rolling_window[1].strftime('%Y%m%d')}",
            'fixedCount': fixed_win['totalCount'],
            'nextMonthCount': next_win['totalCount'],
            'rollingCount': rolling_win['totalCount'],
            'totalWarehouses': len(all_a) + n,
        }
    }

    # ---------- 4. 写入 sample_visualization.json ----------
    viz_path = os.path.join(BASE_DIR, '..', 'frontend', 'public', 'sample_visualization.json')
    with open(viz_path, 'w', encoding='utf-8') as f:
        json.dump(sanitize(visualization_data), f, ensure_ascii=False, indent=1, allow_nan=False)
    print('WROTE:', viz_path, 'size:', os.path.getsize(viz_path) // 1024, 'KB')

    # ---------- 5. 写入 sample_scheduling.json（含 visualization_data） ----------
    end_times = [w['endTime'] for w in b_warehouses if w['endTime']]
    last_end = sorted(end_times)[-1] if end_times else None

    output = {
        'success': True,
        'message': '排仓计算完成（一体化演示数据）',
        'final_mode': '正常模式',
        'final_end_date': last_end,
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
        json.dump(sanitize(output), f, ensure_ascii=False, indent=1, allow_nan=False)
    print('WROTE:', sched_path, 'size:', os.path.getsize(sched_path) // 1024, 'KB')


if __name__ == '__main__':
    main()
