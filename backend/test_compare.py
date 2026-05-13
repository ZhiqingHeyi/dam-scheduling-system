import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '.')
from core.scheduling_algorithm import (
    load_ahp_weights, compute_entropy_weights, compute_combined_weights,
    normalize_for_scoring, sort_warehouses_by_score, correct_layer_order,
    elevation_constraint_sort, extract_dam_ids, extract_layer_ids,
    CraneScheduler, WinterScheduleHandler, SchedulingConfig,
    build_complete_schedule, build_owner_export_table,
    export_plan_windows, reschedule_c_with_winter
)

upload_dir = 'uploads'
base_file = os.path.join(upload_dir, 'BaselineSchedule.xlsx')
actual_file = os.path.join(upload_dir, 'ActualDone.xlsx')
warehouse_file = os.path.join(upload_dir, 'WarehouseData_filled.xlsx')
ahp_file = os.path.join(upload_dir, 'AHPScores.xlsx')

base_df = pd.read_excel(base_file)
for col in ['PlanStart', 'PlanEnd']:
    if col in base_df.columns:
        base_df[col] = pd.to_datetime(base_df[col])

act_df = pd.DataFrame()
if os.path.exists(actual_file):
    act_df = pd.read_excel(actual_file)
    for col in ['ActualStart', 'ActualEnd']:
        if col in act_df.columns:
            act_df[col] = pd.to_datetime(act_df[col])

print(f'Base: {len(base_df)} rows, Act: {len(act_df)} rows')
print(f'Base columns: {list(base_df.columns)}')
ps_min = base_df['PlanStart'].min()
ps_max = base_df['PlanStart'].max()
pe_min = base_df['PlanEnd'].min()
pe_max = base_df['PlanEnd'].max()
print(f'Base PlanStart range: {ps_min} ~ {ps_max}')
print(f'Base PlanEnd range: {pe_min} ~ {pe_max}')
if len(act_df) > 0:
    print(f'Act columns: {list(act_df.columns)}')
    as_min = act_df['ActualStart'].min()
    as_max = act_df['ActualStart'].max()
    print(f'Act ActualStart range: {as_min} ~ {as_max}')

from api.scheduling import split_schedule_abc, make_warehouse_data_b, extract_a_segment_heights

a_idx, b_idx, c_idx, t_cut_plan, b1_idx, b2_idx = split_schedule_abc(base_df, act_df, 20)
print(f'\nABC split: A={len(a_idx)}, B={len(b_idx)}, C={len(c_idx)}')
print(f'T_cut_plan: {t_cut_plan}')

b_data = make_warehouse_data_b(base_df, b_idx, warehouse_file)
print(f'B data: {len(b_data)} rows, columns: {list(b_data.columns)}')

if os.path.exists(ahp_file):
    ahp_weights, cr = load_ahp_weights(ahp_file)
else:
    ahp_weights = np.array([0.25, 0.20, 0.18, 0.15, 0.12, 0.10])
    cr = 0.05

score_indicators = b_data.iloc[:, 1:7].values.astype(float)
entropy_weights = compute_entropy_weights(score_indicators)

config = SchedulingConfig(alpha=0.5)
combined_weights = compute_combined_weights(ahp_weights, entropy_weights, config.alpha)

is_benefit = np.ones(score_indicators.shape[1], dtype=bool)
if score_indicators.shape[1] >= 5:
    is_benefit[4] = False

x_score = normalize_for_scoring(score_indicators, is_benefit)

warehouse_ids = b_data.iloc[:, 0].astype(str).tolist()
dam_ids = extract_dam_ids(warehouse_ids)
layer_ids = extract_layer_ids(warehouse_ids)

sorted_indices, scores = sort_warehouses_by_score(warehouse_ids, x_score, combined_weights)
sorted_indices, sorted_dam, sorted_layer = correct_layer_order(
    sorted_indices, dam_ids, layer_ids, warehouse_ids, scores
)

dam_list_a, heights_a = extract_a_segment_heights(base_df, act_df, a_idx)

final_order = elevation_constraint_sort(
    sorted_indices, dam_ids, layer_ids, score_indicators,
    config.base_elev_const, config.adj_height_limit, config.global_height_limit,
    dam_list_a, heights_a
)

total_cols = len(b_data.columns)
if total_cols >= 4:
    crane_col_name = b_data.columns[-2]
    rest_col_name = b_data.columns[-1]
    crane_data = b_data.iloc[final_order, -2].values
    rest_data = b_data.iloc[final_order, -1].values
else:
    crane_col_name = '缆机数量'
    rest_col_name = '间歇时间'
    crane_data = np.ones(len(final_order))
    rest_data = np.full(len(final_order), 10.0)

sorted_report = pd.DataFrame({
    'WarehouseID': [warehouse_ids[i] for i in final_order],
    'Score': scores[final_order],
    crane_col_name: crane_data,
    rest_col_name: rest_data
})

print(f'\nSorted report (first 5):')
print(sorted_report.head().to_string())

start_dt = datetime(2026, 4, 11)
scheduler = CraneScheduler(config)
schedule_normal = scheduler.schedule_by_crane_and_gap(sorted_report, start_dt, 'normal')

winter_handler = WinterScheduleHandler(config)
schedule_with_winter = winter_handler.apply_winter_to_schedule(schedule_normal)

t_all, t_a_out, t_c_out = build_complete_schedule(
    schedule_with_winter, a_idx, b_idx, c_idx, base_df, act_df, config
)

print(f'\nComplete schedule: {len(t_all)} rows')
print(f'A: {len(t_a_out)}, B: {len(schedule_with_winter)}, C: {len(t_c_out)}')

t_export = build_owner_export_table(t_all)
print(f'\nExport table: {len(t_export)} rows, columns: {list(t_export.columns)}')
print(t_export.head(10).to_string())

# Compare with MATLAB
mat_dir = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\输出结果\Run_20260314_235628'
mat_df = pd.read_excel(os.path.join(mat_dir, '完整排仓计划.xlsx'))
print(f'\nMATLAB export: {len(mat_df)} rows')
print(mat_df.head(10).to_string())

# Detailed comparison
print('\n=== 差异对比（前20行） ===')
n_compare = min(20, len(t_export), len(mat_df))
match_count = 0
for i in range(n_compare):
    py_row = t_export.iloc[i]
    mat_row = mat_df.iloc[i]
    diff = []
    for col in t_export.columns:
        if col in mat_df.columns:
            py_val = str(py_row[col])
            mat_val = str(mat_row[col])
            if py_val != mat_val:
                diff.append(f'{col}: Python={py_val}, MATLAB={mat_val}')
    if diff:
        print(f'Row {i}: {diff}')
    else:
        match_count += 1
        print(f'Row {i}: 一致')

print(f'\n匹配率: {match_count}/{n_compare}')

# Save test output
test_dir = 'output/test_run_v2'
os.makedirs(test_dir, exist_ok=True)
t_export.to_excel(os.path.join(test_dir, '完整排仓计划.xlsx'), index=False)
plan_files = export_plan_windows(t_all, test_dir)
print(f'\n输出文件已保存到: {test_dir}')
for f in os.listdir(test_dir):
    if f.endswith('.xlsx'):
        fp = os.path.join(test_dir, f)
        df = pd.read_excel(fp)
        print(f'  {f}: {len(df)} rows')
