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
from api.scheduling import split_schedule_abc, make_warehouse_data_b, extract_a_segment_heights

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

a_idx, b_idx, c_idx, t_cut_plan, b1_idx, b2_idx = split_schedule_abc(base_df, act_df, 20)
b_data = make_warehouse_data_b(base_df, b_idx, warehouse_file)

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

print('=== B段排序结果 ===')
print(sorted_report.to_string())

start_dt = datetime(2026, 4, 11)
scheduler = CraneScheduler(config)
schedule_normal = scheduler.schedule_by_crane_and_gap(sorted_report, start_dt, 'normal')

print('\n=== B段排班结果（冬歇期前） ===')
for i in range(len(schedule_normal)):
    wid = schedule_normal.iloc[i]['WarehouseID']
    s = schedule_normal.iloc[i]['开始时间']
    e = schedule_normal.iloc[i]['结束时间']
    print(f'{wid}: {s} ~ {e}')

winter_handler = WinterScheduleHandler(config)
schedule_with_winter = winter_handler.apply_winter_to_schedule(schedule_normal)

print('\n=== B段排班结果（冬歇期后） ===')
for i in range(len(schedule_with_winter)):
    wid = schedule_with_winter.iloc[i]['WarehouseID']
    s = schedule_with_winter.iloc[i]['开始时间']
    e = schedule_with_winter.iloc[i]['结束时间']
    print(f'{wid}: {s} ~ {e}')

# Also check MATLAB's sorted report
mat_dir = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\输出结果\Run_20260314_235628'
mat_opt = os.path.join(mat_dir, 'OptimalSchedule.xlsx')
if os.path.exists(mat_opt):
    mat_sorted = pd.read_excel(mat_opt)
    print('\n=== MATLAB排序结果 ===')
    print(mat_sorted.to_string())
