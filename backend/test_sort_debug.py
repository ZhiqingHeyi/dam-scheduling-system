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
print('=== After sortWarehousesByScore ===')
for i, idx in enumerate(sorted_indices):
    print(f'{i}: {warehouse_ids[idx]} score={scores[idx]:.6f} dam={dam_ids[idx]} layer={layer_ids[idx]}')

sorted_indices, sorted_dam, sorted_layer = correct_layer_order(
    sorted_indices, dam_ids, layer_ids, warehouse_ids, scores
)
print('\n=== After correctLayerOrder ===')
for i, idx in enumerate(sorted_indices):
    print(f'{i}: {warehouse_ids[idx]} score={scores[idx]:.6f} dam={dam_ids[idx]} layer={layer_ids[idx]}')

dam_list_a, heights_a = extract_a_segment_heights(base_df, act_df, a_idx)
print(f'\n=== A段坝段高度 ===')
for d, h in zip(dam_list_a, heights_a):
    print(f'  Dam {d}: H={h}')

# Debug elevation constraint sort
H_all = config.base_elev_const - score_indicators[:, 0]
print(f'\n=== B段仓面高程 ===')
for i, idx in enumerate(sorted_indices):
    wid = warehouse_ids[idx]
    h = H_all[idx]
    print(f'{wid}: H={h:.1f}')

# Now run with debug
final_order = elevation_constraint_sort(
    sorted_indices, dam_ids, layer_ids, score_indicators,
    config.base_elev_const, config.adj_height_limit, config.global_height_limit,
    dam_list_a, heights_a
)

print('\n=== After elevationConstraintSort ===')
for i, idx in enumerate(final_order):
    print(f'{i}: {warehouse_ids[idx]} score={scores[idx]:.6f} dam={dam_ids[idx]} layer={layer_ids[idx]} H={H_all[idx]:.1f}')

# MATLAB order for comparison
mat_order = ['15-3', '19-5', '20-5', '18-4', '19-6', '17-6', '16-5', '21-1', '17-7', '16-6',
             '21-2', '18-5', '15-4', '17-8', '19-7', '16-7', '14-1', '18-6', '20-6', '21-3']
print('\n=== MATLAB Order ===')
for i, wid in enumerate(mat_order):
    idx = warehouse_ids.index(wid)
    print(f'{i}: {wid} score={scores[idx]:.6f} dam={dam_ids[idx]} layer={layer_ids[idx]} H={H_all[idx]:.1f}')
