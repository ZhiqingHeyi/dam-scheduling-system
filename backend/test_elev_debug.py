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
    SchedulingConfig
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

dam_list_a, heights_a = extract_a_segment_heights(base_df, act_df, a_idx)
print('=== Python A段坝段高度 ===')
for d, h in zip(dam_list_a, heights_a):
    print(f'  Dam {d}: H={h}')

# Now simulate MATLAB's logic
# MATLAB: uDam = unique(damID) where damID is from sorted order after correctLayerOrder
# MATLAB: currentH is initialized from A段 heights
# The key is: MATLAB's uDam is sorted, and the index mapping is:
# uDam(1)=14, uDam(2)=15, uDam(3)=16, uDam(4)=17, uDam(5)=18, uDam(6)=19, uDam(7)=20, uDam(8)=21

# MATLAB's A段 heights:
# damList_A = [19, 17, 18, 20, 16, 15] (from unique of Dam_act)
# H_A = [762, 765, 759, 762, 762, 756]

# After initialization:
# currentH(1)=NaN (Dam 14)
# currentH(2)=756 (Dam 15, from A段)
# currentH(3)=762 (Dam 16, from A段)
# currentH(4)=765 (Dam 17, from A段)
# currentH(5)=759 (Dam 18, from A段)
# currentH(6)=762 (Dam 19, from A段)
# currentH(7)=762 (Dam 20, from A段)
# currentH(8)=NaN (Dam 21)

# Now let's trace the elevation constraint sort step by step
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

H_all = config.base_elev_const - score_indicators[:, 0]
H_sorted = H_all[sorted_indices]

u_dam = np.unique(dam_ids[sorted_indices][~np.isnan(dam_ids[sorted_indices])])
n_dam = len(u_dam)
dam_index_map = {int(d): k for k, d in enumerate(u_dam)}

print(f'\nu_dam = {u_dam}')
print(f'dam_index_map = {dam_index_map}')

# Initialize currentH from A段
current_h = np.full(n_dam, np.nan)
for k, d in enumerate(u_dam):
    d_int = int(d)
    if d_int in dam_list_a:
        idx_a = dam_list_a.index(d_int)
        if idx_a < len(heights_a) and not np.isnan(heights_a[idx_a]):
            current_h[k] = heights_a[idx_a]

print(f'\nInitial current_h = {current_h}')

# Now trace the sort
dam_index_row = np.full(len(sorted_indices), -1, dtype=int)
for i in range(len(sorted_indices)):
    d = dam_ids[sorted_indices[i]]
    if not np.isnan(d) and int(d) in dam_index_map:
        dam_index_row[i] = dam_index_map[int(d)]

print(f'\ndam_index_row = {dam_index_row}')
print(f'H_sorted = {H_sorted}')

# Step-by-step trace
used = np.zeros(len(sorted_indices), dtype=bool)
final_order = []

print('\n=== Step-by-step elevation constraint sort ===')
for pos in range(len(sorted_indices)):
    placed = False
    chosen = -1
    
    for i in range(len(sorted_indices)):
        if used[i]:
            continue
        
        di = dam_index_row[i]
        Hi = H_sorted[i]
        wid = warehouse_ids[sorted_indices[i]]
        
        if di < 0 or np.isnan(Hi):
            print(f'  pos={pos}: i={i} {wid} di={di} Hi={Hi} -> no dam info, placed directly')
            placed = True
            chosen = i
            break
        
        temp_h = current_h.copy()
        temp_h[di] = Hi
        
        ok = True
        reason = ''
        
        if di - 1 >= 0:
            Hj = temp_h[di - 1]
            if not np.isnan(Hj) and not np.isnan(temp_h[di]):
                diff = abs(temp_h[di] - Hj)
                if diff > config.adj_height_limit:
                    ok = False
                    reason = f'adj_diff={diff:.0f} (dam {u_dam[di-1]:.0f} H={Hj:.0f})'
        
        if ok and di + 1 <= n_dam - 1:
            Hj = temp_h[di + 1]
            if not np.isnan(Hj) and not np.isnan(temp_h[di]):
                diff = abs(temp_h[di] - Hj)
                if diff > config.adj_height_limit:
                    ok = False
                    reason = f'adj_diff={diff:.0f} (dam {u_dam[di+1]:.0f} H={Hj:.0f})'
        
        if ok:
            h_non_na = temp_h[~np.isnan(temp_h)]
            if len(h_non_na) > 0:
                global_diff = h_non_na.max() - h_non_na.min()
                if global_diff > config.global_height_limit:
                    ok = False
                    reason = f'global_diff={global_diff:.0f} (max={h_non_na.max():.0f} min={h_non_na.min():.0f})'
        
        if ok:
            print(f'  pos={pos}: i={i} {wid} di={di} Hi={Hi:.0f} -> OK, placed')
            placed = True
            chosen = i
            current_h = temp_h
            break
        else:
            pass  # Skip, try next
    
    if not placed:
        chosen = int(np.where(~used)[0][0])
        di = dam_index_row[chosen]
        Hi = H_sorted[chosen]
        wid = warehouse_ids[sorted_indices[chosen]]
        if di >= 0 and not np.isnan(Hi):
            current_h[di] = Hi
        print(f'  pos={pos}: {wid} -> FORCED (no constraint satisfied)')
    
    final_order.append(sorted_indices[chosen])
    used[chosen] = True

print('\n=== Final order ===')
for i, idx in enumerate(final_order):
    print(f'{i}: {warehouse_ids[idx]} H={H_all[idx]:.0f}')
