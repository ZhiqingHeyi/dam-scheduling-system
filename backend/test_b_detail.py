import pandas as pd
import sys
sys.path.insert(0, '.')
from api.scheduling import split_schedule_abc

base_df = pd.read_excel('./uploads/BaselineSchedule.xlsx')
for c in ['PlanStart', 'PlanEnd']:
    base_df[c] = pd.to_datetime(base_df[c])

act_df = pd.read_excel('./uploads/ActualDone.xlsx')
for c in ['ActualStart', 'ActualEnd']:
    act_df[c] = pd.to_datetime(act_df[c])

a_idx, b_idx, c_idx, t_cut_plan, b1_idx, b2_idx = split_schedule_abc(base_df, act_df, 10)

print(f"t_cut_plan = {t_cut_plan}")
print(f"A段: {len(a_idx)}, B段: {len(b_idx)}, C段: {len(c_idx)}")
print(f"B1: {len(b1_idx)}, B2: {len(b2_idx)}")

before_mask = base_df['PlanEnd'] <= t_cut_plan
after_mask = base_df['PlanEnd'] > t_cut_plan
print(f"\nPlanEnd <= t_cut_plan: {before_mask.sum()}")
print(f"PlanEnd > t_cut_plan: {after_mask.sum()}")

is_a_set = set(a_idx)
before_not_a = [i for i in range(len(base_df)) if before_mask.iloc[i] and i not in is_a_set]
print(f"Before t_cut_plan but not A: {len(before_not_a)}")

if len(before_not_a) > 0:
    b1_ids = [f"{int(base_df.iloc[i]['DamID'])}-{int(base_df.iloc[i]['LayerID'])}" for i in before_not_a[:20]]
    print(f"  First 20: {b1_ids}")

after_not_a = [i for i in range(len(base_df)) if after_mask.iloc[i] and i not in is_a_set]
print(f"\nAfter t_cut_plan and not A: {len(after_not_a)}")
if len(after_not_a) > 0:
    after_ids = [f"{int(base_df.iloc[i]['DamID'])}-{int(base_df.iloc[i]['LayerID'])}" for i in after_not_a[:20]]
    print(f"  First 20: {after_ids}")

print(f"\n=== Check A segment IDs ===")
a_ids = [f"{int(base_df.iloc[i]['DamID'])}-{int(base_df.iloc[i]['LayerID'])}" for i in a_idx]
print(f"A IDs: {a_ids}")

print(f"\n=== Check MATLAB WarehouseData IDs vs Python B IDs ===")
mat_wh_ids = ['15-3', '19-5', '17-6', '21-1', '16-5', '18-4', '20-5', '17-7', '19-6', '16-6',
              '15-7', '17-7', '19-7', '21-1', '14-2', '16-5', '18-5', '21-2', '15-8', '17-8',
              '19-8', '14-3', '16-6', '18-6', '21-3', '17-9', '19-9', '14-4', '16-7', '18-7',
              '20-6', '13-1', '15-9', '17-10', '19-10', '19-11', '21-4', '16-8', '18-8', '13-2',
              '20-7', '17-11', '21-5', '13-3', '20-8', '18-9', '15-10', '21-6', '17-12', '19-12',
              '14-5', '22-1', '16-9']

for mat_id in mat_wh_ids:
    parts = mat_id.split('-')
    dam, layer = int(parts[0]), int(parts[1])
    mask = (base_df['DamID'] == dam) & (base_df['LayerID'] == layer)
    if mask.any():
        idx = base_df[mask].index[0]
        plan_end = base_df.iloc[idx]['PlanEnd']
        in_a = idx in is_a_set
        in_b = idx in set(b_idx)
        segment = 'A' if in_a else ('B' if in_b else 'C')
        print(f"  {mat_id}: PlanEnd={plan_end.strftime('%Y/%m/%d')}, segment={segment}")
    else:
        print(f"  {mat_id}: NOT FOUND in base_df")
