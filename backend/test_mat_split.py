import pandas as pd
import numpy as np

mat_base_file = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\BaselineSchedule.xlsx'
mat_base = pd.read_excel(mat_base_file, header=None, skiprows=2)
print(f"MATLAB BaselineSchedule raw: {mat_base.shape}")

mat_base.columns = ['idx', 'DamID', 'LayerID', 'PlanStart', 'PlanEnd'] + [f'col{i}' for i in range(5, len(mat_base.columns))]
mat_base = mat_base.dropna(subset=['DamID', 'LayerID', 'PlanStart', 'PlanEnd'])
mat_base['DamID'] = mat_base['DamID'].astype(int)
mat_base['LayerID'] = mat_base['LayerID'].astype(int)
mat_base['PlanStart'] = pd.to_datetime(mat_base['PlanStart'])
mat_base['PlanEnd'] = pd.to_datetime(mat_base['PlanEnd'])
mat_base = mat_base.sort_values(['PlanStart', 'PlanEnd', 'DamID', 'LayerID']).reset_index(drop=True)
print(f"MATLAB BaselineSchedule clean: {len(mat_base)} rows")

mat_base_ids = [f"{d}-{l}" for d, l in zip(mat_base['DamID'], mat_base['LayerID'])]
print(f"MATLAB unique IDs: {len(set(mat_base_ids))}")

our_base = pd.read_excel('./uploads/BaselineSchedule.xlsx')
for c in ['PlanStart', 'PlanEnd']:
    our_base[c] = pd.to_datetime(our_base[c])
print(f"\nOur BaselineSchedule: {len(our_base)} rows")
our_base_ids = [f"{int(d)}-{int(l)}" for d, l in zip(our_base['DamID'], our_base['LayerID'])]
print(f"Our unique IDs: {len(set(our_base_ids))}")

mat_only = set(mat_base_ids) - set(our_base_ids)
our_only = set(our_base_ids) - set(mat_base_ids)
print(f"\nIn MATLAB but not ours: {len(mat_only)}")
if mat_only:
    print(f"  Sample: {list(mat_only)[:10]}")
print(f"In ours but not MATLAB: {len(our_only)}")
if our_only:
    print(f"  Sample: {list(our_only)[:10]}")

mat_act_file = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\ActualDone.xlsx'
import os
if os.path.exists(mat_act_file):
    mat_act = pd.read_excel(mat_act_file, header=None, skiprows=2)
    print(f"\nMATLAB ActualDone raw: {mat_act.shape}")
    print(mat_act.head(5).to_string())

our_act = pd.read_excel('./uploads/ActualDone.xlsx')
for c in ['ActualStart', 'ActualEnd']:
    our_act[c] = pd.to_datetime(our_act[c])
print(f"\nOur ActualDone: {len(our_act)} rows")
print(our_act.head(5).to_string())

mat_act_ids = []
if os.path.exists(mat_act_file):
    for _, row in mat_act.iterrows():
        try:
            d, l = int(row.iloc[0]), int(row.iloc[1])
            mat_act_ids.append(f"{d}-{l}")
        except:
            pass
    print(f"\nMATLAB ActualDone IDs: {mat_act_ids}")

our_act_ids = [f"{int(d)}-{int(l)}" for d, l in zip(our_act['DamID'], our_act['LayerID'])]
print(f"Our ActualDone IDs: {our_act_ids}")

if mat_act_ids and our_act_ids:
    print(f"Match: {set(mat_act_ids) == set(our_act_ids)}")

t_cut_plan_mat = mat_base[mat_base['DamID'].astype(str) + '-' + mat_base['LayerID'].astype(str)].apply(
    lambda r: f"{int(r['DamID'])}-{int(r['LayerID'])}", axis=1)

print(f"\n=== Simulating MATLAB splitScheduleABC ===")
mat_act_dam = []
mat_act_layer = []
mat_act_end = []
if os.path.exists(mat_act_file):
    for _, row in mat_act.iterrows():
        try:
            d, l = int(row.iloc[0]), int(row.iloc[1])
            ae = pd.to_datetime(row.iloc[3])
            mat_act_dam.append(d)
            mat_act_layer.append(l)
            mat_act_end.append(ae)
        except:
            pass

if mat_act_dam:
    matched_idx = []
    plan_finish_done = []
    for d, l in zip(mat_act_dam, mat_act_layer):
        mask = (mat_base['DamID'] == d) & (mat_base['LayerID'] == l)
        if mask.any():
            idx = mat_base[mask].index[0]
            matched_idx.append(idx)
            plan_finish_done.append(mat_base.loc[idx, 'PlanEnd'])
    
    valid = [i for i in range(len(plan_finish_done)) if not pd.isna(plan_finish_done[i])]
    if valid:
        t_cut = max([plan_finish_done[i] for i in valid])
        print(f"MATLAB t_cut_plan = {t_cut}")
        
        a_idx = list(set([matched_idx[i] for i in valid]))
        mask_before = mat_base['PlanEnd'] <= t_cut
        mask_after = mat_base['PlanEnd'] > t_cut
        is_a = [i in a_idx for i in range(len(mat_base))]
        
        b1_idx = [i for i in range(len(mat_base)) if mask_before.iloc[i] and not is_a[i]]
        after_indices = [i for i in range(len(mat_base)) if mask_after.iloc[i] and not is_a[i]]
        after_sorted = sorted(after_indices, key=lambda x: mat_base.loc[x, 'PlanEnd'])
        b2_idx = after_sorted[:10]
        b_idx = list(set(b1_idx + b2_idx))
        
        print(f"A={len(a_idx)}, B={len(b_idx)}, B1={len(b1_idx)}, B2={len(b2_idx)}")
        
        b_ids = [f"{int(mat_base.iloc[i]['DamID'])}-{int(mat_base.iloc[i]['LayerID'])}" for i in b_idx]
        print(f"B IDs: {b_ids}")
