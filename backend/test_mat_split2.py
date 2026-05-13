import pandas as pd
import numpy as np

mat_base_file = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\BaselineSchedule.xlsx'
mat_base = pd.read_excel(mat_base_file, header=None, skiprows=2)
mat_base.columns = ['idx', 'DamID', 'LayerID', 'PlanStart', 'PlanEnd'] + [f'col{i}' for i in range(5, len(mat_base.columns))]
mat_base = mat_base.dropna(subset=['DamID', 'LayerID', 'PlanStart', 'PlanEnd'])
mat_base['DamID'] = mat_base['DamID'].astype(int)
mat_base['LayerID'] = mat_base['LayerID'].astype(int)
mat_base['PlanStart'] = pd.to_datetime(mat_base['PlanStart']) + pd.Timedelta(days=1)
mat_base['PlanEnd'] = pd.to_datetime(mat_base['PlanEnd']) + pd.Timedelta(days=1)
mat_base = mat_base.sort_values(['PlanStart', 'PlanEnd', 'DamID', 'LayerID']).reset_index(drop=True)
print(f"MATLAB BaselineSchedule: {len(mat_base)} rows")

mat_act_file = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\ActualDone.xlsx'
mat_act = pd.read_excel(mat_act_file, header=None, skiprows=2)
mat_act.columns = ['DamID', 'LayerID', 'ActualStart', 'ActualEnd']
mat_act = mat_act.dropna(subset=['DamID', 'LayerID'])
mat_act['DamID'] = mat_act['DamID'].astype(int)
mat_act['LayerID'] = mat_act['LayerID'].astype(int)
mat_act['ActualStart'] = pd.to_datetime(mat_act['ActualStart']) + pd.Timedelta(days=1)
mat_act['ActualEnd'] = pd.to_datetime(mat_act['ActualEnd']) + pd.Timedelta(days=1)
print(f"MATLAB ActualDone: {len(mat_act)} rows")

print(f"\n=== Simulating MATLAB splitScheduleABC ===")
matched_idx = []
plan_finish_done = []
for _, row in mat_act.iterrows():
    d, l = row['DamID'], row['LayerID']
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
    b1_ids = [f"{int(mat_base.iloc[i]['DamID'])}-{int(mat_base.iloc[i]['LayerID'])}" for i in b1_idx]
    b2_ids = [f"{int(mat_base.iloc[i]['DamID'])}-{int(mat_base.iloc[i]['LayerID'])}" for i in b2_idx]
    print(f"B1 IDs: {b1_ids}")
    print(f"B2 IDs: {b2_ids}")
    print(f"B IDs: {b_ids}")

print(f"\n=== Python split_schedule_abc ===")
our_base = pd.read_excel('./uploads/BaselineSchedule.xlsx')
for c in ['PlanStart', 'PlanEnd']:
    our_base[c] = pd.to_datetime(our_base[c])
our_act = pd.read_excel('./uploads/ActualDone.xlsx')
for c in ['ActualStart', 'ActualEnd']:
    our_act[c] = pd.to_datetime(our_act[c])

from api.scheduling import split_schedule_abc
a_idx2, b_idx2, c_idx2, t_cut2, b1_idx2, b2_idx2 = split_schedule_abc(our_base, our_act, 10)
print(f"Python t_cut_plan = {t_cut2}")
print(f"A={len(a_idx2)}, B={len(b_idx2)}, B1={len(b1_idx2)}, B2={len(b2_idx2)}")
b_ids2 = [f"{int(our_base.iloc[i]['DamID'])}-{int(our_base.iloc[i]['LayerID'])}" for i in b_idx2]
b1_ids2 = [f"{int(our_base.iloc[i]['DamID'])}-{int(our_base.iloc[i]['LayerID'])}" for i in b1_idx2]
b2_ids2 = [f"{int(our_base.iloc[i]['DamID'])}-{int(our_base.iloc[i]['LayerID'])}" for i in b2_idx2]
print(f"B1 IDs: {b1_ids2}")
print(f"B2 IDs: {b2_ids2}")
print(f"B IDs: {b_ids2}")

print(f"\n=== Key Difference Analysis ===")
print(f"MATLAB ActualDone: {len(mat_act)} rows, Python ActualDone: {len(our_act)} rows")
mat_act_ids = set([f"{int(d)}-{int(l)}" for d, l in zip(mat_act['DamID'], mat_act['LayerID'])])
our_act_ids = set([f"{int(d)}-{int(l)}" for d, l in zip(our_act['DamID'], our_act['LayerID'])])
print(f"MATLAB only: {mat_act_ids - our_act_ids}")
print(f"Python only: {our_act_ids - mat_act_ids}")
