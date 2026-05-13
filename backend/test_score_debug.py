import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, '.')
from core.scheduling_algorithm import (
    load_ahp_weights, compute_entropy_weights, compute_combined_weights,
    normalize_for_scoring, sort_warehouses_by_score, correct_layer_order,
    extract_dam_ids, extract_layer_ids, SchedulingConfig
)
from api.scheduling import split_schedule_abc, make_warehouse_data_b

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

print('=== B段仓面数据 ===')
print(b_data.to_string())

if os.path.exists(ahp_file):
    ahp_weights, cr = load_ahp_weights(ahp_file)
else:
    ahp_weights = np.array([0.25, 0.20, 0.18, 0.15, 0.12, 0.10])
    cr = 0.05

score_indicators = b_data.iloc[:, 1:7].values.astype(float)
print('\n=== Score Indicators ===')
print(score_indicators)

entropy_weights = compute_entropy_weights(score_indicators)
print(f'\n=== Entropy Weights ===\n{entropy_weights}')

config = SchedulingConfig(alpha=0.5)
combined_weights = compute_combined_weights(ahp_weights, entropy_weights, config.alpha)
print(f'\n=== Combined Weights ===\n{combined_weights}')

is_benefit = np.ones(score_indicators.shape[1], dtype=bool)
if score_indicators.shape[1] >= 5:
    is_benefit[4] = False

x_score = normalize_for_scoring(score_indicators, is_benefit)
print('\n=== Normalized Score Data ===')
print(x_score)

scores = x_score @ combined_weights
print('\n=== Scores ===')
warehouse_ids = b_data.iloc[:, 0].astype(str).tolist()
for i, (wid, s) in enumerate(zip(warehouse_ids, scores)):
    print(f'{wid}: {s:.6f}')

sorted_indices = np.argsort(-scores).tolist()
print('\n=== Sorted by Score (desc) ===')
for i, idx in enumerate(sorted_indices):
    print(f'{i}: {warehouse_ids[idx]} score={scores[idx]:.6f}')

# Now check MATLAB's WarehouseData
mat_warehouse_file = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\WarehouseData.xlsx'
if os.path.exists(mat_warehouse_file):
    mat_wh = pd.read_excel(mat_warehouse_file)
    print('\n=== MATLAB WarehouseData ===')
    print(mat_wh.to_string())
