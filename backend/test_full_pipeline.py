import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '.')
from api.scheduling import split_schedule_abc, make_warehouse_data_b, extract_a_segment_heights
from core.scheduling_algorithm import (
    load_ahp_weights, compute_entropy_weights, compute_combined_weights,
    normalize_for_scoring, sort_warehouses_by_score, correct_layer_order,
    elevation_constraint_sort, extract_dam_ids, extract_layer_ids,
    CraneScheduler, WinterScheduleHandler, SchedulingConfig,
    build_complete_schedule, build_owner_export_table
)

upload_dir = './uploads'
base_file = os.path.join(upload_dir, 'BaselineSchedule.xlsx')
actual_file = os.path.join(upload_dir, 'ActualDone.xlsx')
warehouse_file = os.path.join(upload_dir, 'WarehouseData_filled.xlsx')
ahp_file = os.path.join(upload_dir, 'AHPScores.xlsx')

print("=== Step 1: Load data ===")
base_df = pd.read_excel(base_file)
for col in ['PlanStart', 'PlanEnd']:
    if col in base_df.columns:
        base_df[col] = pd.to_datetime(base_df[col])
print(f"  Base schedule: {len(base_df)} rows")

act_df = pd.DataFrame()
if os.path.exists(actual_file):
    act_df = pd.read_excel(actual_file)
    for col in ['ActualStart', 'ActualEnd']:
        if col in act_df.columns:
            act_df[col] = pd.to_datetime(act_df[col])
print(f"  Actual done: {len(act_df)} rows")

print("\n=== Step 2: Split ABC ===")
a_idx, b_idx, c_idx, t_cut_plan, b1_idx, b2_idx = split_schedule_abc(base_df, act_df, 10)
print(f"  A段: {len(a_idx)}, B段: {len(b_idx)}, C段: {len(c_idx)}")
print(f"  B1(已过计划): {len(b1_idx)}, B2(额外选取): {len(b2_idx)}")

b_ids = [f"{int(base_df.iloc[i]['DamID'])}-{int(base_df.iloc[i]['LayerID'])}" for i in b_idx]
print(f"  B段仓面: {b_ids}")

mat_b_ids = ['15-3', '19-5', '17-6', '21-1', '16-5', '18-4', '20-5', '17-7', '19-6', '16-6',
             '15-7', '17-7', '19-7', '21-1', '14-2', '16-5', '18-5', '21-2', '15-8', '17-8',
             '19-8', '14-3', '16-6', '18-6', '21-3', '17-9', '19-9', '14-4', '16-7', '18-7',
             '20-6', '13-1', '15-9', '17-10', '19-10', '19-11', '21-4', '16-8', '18-8', '13-2',
             '20-7', '17-11', '21-5', '13-3', '20-8', '18-9', '15-10', '21-6', '17-12', '19-12',
             '14-5', '22-1', '16-9']
print(f"  MATLAB B段仓面数: {len(mat_b_ids)}")
common = set(b_ids) & set(mat_b_ids)
print(f"  与MATLAB重叠: {len(common)}/{len(b_ids)}")

print("\n=== Step 3: Generate B段 warehouse data ===")
b_data = make_warehouse_data_b(base_df, b_idx, warehouse_file)
print(f"  B段数据: {len(b_data)} rows, {len(b_data.columns)} cols")
print(f"  Columns: {list(b_data.columns)}")
if len(b_data) > 0:
    print(f"  First 5 rows:")
    for i in range(min(5, len(b_data))):
        row = b_data.iloc[i]
        wid = row.iloc[0]
        crane = row.iloc[-2] if len(row) > 7 else '?'
        rest = row.iloc[-1] if len(row) > 8 else '?'
        print(f"    {wid}: crane={crane}, rest={rest}")

print("\n=== Step 4: Calculate weights ===")
if os.path.exists(ahp_file):
    ahp_weights, cr = load_ahp_weights(ahp_file)
else:
    ahp_weights = np.array([0.25, 0.20, 0.18, 0.15, 0.12, 0.10])
    cr = 0.05
print(f"  AHP weights: {ahp_weights}")
print(f"  CR: {cr}")

score_indicators = b_data.iloc[:, 1:7].values.astype(float)
entropy_weights = compute_entropy_weights(score_indicators)
print(f"  Entropy weights: {entropy_weights}")

config = SchedulingConfig(alpha=0.5)
combined_weights = compute_combined_weights(ahp_weights, entropy_weights, config.alpha)
print(f"  Combined weights: {combined_weights}")

print("\n=== Step 5: Normalize and sort ===")
is_benefit = np.ones(score_indicators.shape[1], dtype=bool)
if score_indicators.shape[1] >= 5:
    is_benefit[4] = False

x_score = normalize_for_scoring(score_indicators, is_benefit)

warehouse_ids = b_data.iloc[:, 0].astype(str).tolist()
dam_ids = extract_dam_ids(warehouse_ids)
layer_ids = extract_layer_ids(warehouse_ids)

sorted_indices, scores = sort_warehouses_by_score(warehouse_ids, x_score, combined_weights)
print(f"  Score-sorted order: {[warehouse_ids[i] for i in sorted_indices[:10]]}")

sorted_indices, sorted_dam, sorted_layer = correct_layer_order(
    sorted_indices, dam_ids, layer_ids, warehouse_ids, scores
)
print(f"  After layer correction: {[warehouse_ids[i] for i in sorted_indices[:10]]}")

dam_list_a, heights_a = extract_a_segment_heights(base_df, act_df, a_idx)
print(f"  A段坝段: {dam_list_a}")
print(f"  A段高度: {heights_a}")

final_order = elevation_constraint_sort(
    sorted_indices, dam_ids, layer_ids, score_indicators,
    config.base_elev_const, config.adj_height_limit, config.global_height_limit,
    dam_list_a, heights_a
)
print(f"  After elevation constraint: {[warehouse_ids[i] for i in final_order[:10]]}")

print("\n=== Step 6: Crane scheduling ===")
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
print(f"  Sorted report (first 10):")
for i in range(min(10, len(sorted_report))):
    row = sorted_report.iloc[i]
    print(f"    {row['WarehouseID']}: Score={row['Score']:.4f}, crane={row[crane_col_name]}, rest={row[rest_col_name]}")

start_dt = datetime(2026, 4, 11)
scheduler = CraneScheduler(config)
schedule_normal = scheduler.schedule_by_crane_and_gap(sorted_report, start_dt, 'normal')
print(f"\n  Schedule (first 10):")
for i in range(min(10, len(schedule_normal))):
    row = schedule_normal.iloc[i]
    print(f"    {row['WarehouseID']}: {row['开始时间'].strftime('%Y/%m/%d')} ~ {row['结束时间'].strftime('%Y/%m/%d')}")

print("\n=== Step 7: Winter schedule ===")
winter_handler = WinterScheduleHandler(config)
schedule_with_winter = winter_handler.apply_winter_to_schedule(schedule_normal)
print(f"  After winter (first 10):")
for i in range(min(10, len(schedule_with_winter))):
    row = schedule_with_winter.iloc[i]
    print(f"    {row['WarehouseID']}: {row['开始时间'].strftime('%Y/%m/%d')} ~ {row['结束时间'].strftime('%Y/%m/%d')}")

print("\n=== Step 8: Build complete schedule ===")
t_all, t_a_out, t_c_out = build_complete_schedule(
    schedule_with_winter, a_idx, b_idx, c_idx, base_df, act_df, config
)
print(f"  Total rows: {len(t_all)}")
print(f"  A段: {len(t_a_out)}, C段: {len(t_c_out)}")

t_export = build_owner_export_table(t_all)
print(f"\n  Export table (first 30):")
for i in range(min(30, len(t_export))):
    row = t_export.iloc[i]
    print(f"    {row['编号']}: PlanEnd={row['计划结束时间']}, PlanStart={row['计划开始时间']}, ActualStart={row['实际开始时间']}, ActualEnd={row['实际结束时间']}")

print("\n=== Step 9: Compare with MATLAB ===")
mat_dir = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\输出结果\Run_20260314_235628'
comb_file = os.path.join(mat_dir, '完整排仓计划.xlsx')
mat_comb = pd.read_excel(comb_file)

print(f"  MATLAB total rows: {len(mat_comb)}")
print(f"  Python total rows: {len(t_export)}")

match_count = 0
mismatch_count = 0
for i in range(min(len(t_export), len(mat_comb))):
    py_row = t_export.iloc[i]
    mat_row = mat_comb.iloc[i]
    py_id = str(py_row['编号'])
    mat_id = str(mat_row['编号'])

    if py_id == mat_id:
        py_as = str(py_row['实际开始时间'])
        mat_as = str(mat_row['实际开始时间'])
        py_ae = str(py_row['实际结束时间'])
        mat_ae = str(mat_row['实际结束时间'])

        if py_as == mat_as and py_ae == mat_ae:
            match_count += 1
        else:
            mismatch_count += 1
            if mismatch_count <= 15:
                print(f"  MISMATCH row {i}: {py_id}")
                print(f"    Python:  ActualStart={py_as}, ActualEnd={py_ae}")
                print(f"    MATLAB:  ActualStart={mat_as}, ActualEnd={mat_ae}")
    else:
        mismatch_count += 1
        if mismatch_count <= 15:
            print(f"  ID MISMATCH row {i}: Python={py_id}, MATLAB={mat_id}")

print(f"\n  Match: {match_count}, Mismatch: {mismatch_count}, Total: {min(len(t_export), len(mat_comb))}")
