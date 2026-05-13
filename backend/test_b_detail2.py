import pandas as pd
import numpy as np
import os

base_df = pd.read_excel('./uploads/BaselineSchedule.xlsx')
for c in ['PlanStart', 'PlanEnd']:
    base_df[c] = pd.to_datetime(base_df[c])

print(f"Base schedule: {len(base_df)} rows")
print(f"Columns: {list(base_df.columns)}")

act_df = pd.read_excel('./uploads/ActualDone.xlsx')
for c in ['ActualStart', 'ActualEnd']:
    act_df[c] = pd.to_datetime(act_df[c])

print(f"Actual done: {len(act_df)} rows")
print(f"Columns: {list(act_df.columns)}")

print(f"\n=== A段仓面 (ActualDone) ===")
for _, row in act_df.iterrows():
    d, l = int(row['DamID']), int(row['LayerID'])
    as_ = row['ActualStart'].strftime('%Y/%m/%d')
    ae = row['ActualEnd'].strftime('%Y/%m/%d')
    mask = (base_df['DamID'] == d) & (base_df['LayerID'] == l)
    if mask.any():
        pe = base_df[mask].iloc[0]['PlanEnd'].strftime('%Y/%m/%d')
        ps = base_df[mask].iloc[0]['PlanStart'].strftime('%Y/%m/%d')
    else:
        pe = ps = '?'
    print(f"  {d}-{l}: PlanEnd={pe}, ActualEnd={ae}")

t_cut_plan = act_df['ActualEnd'].max()
print(f"\nt_cut_plan (max ActualEnd) = {t_cut_plan.strftime('%Y/%m/%d')}")

base_plan_end_max = base_df[base_df['DamID'].isin(act_df['DamID'].values) & 
                             base_df['LayerID'].isin(act_df['LayerID'].values)]['PlanEnd'].max()
print(f"Base PlanEnd max for A段 = {base_plan_end_max.strftime('%Y/%m/%d')}")

before_cut = base_df[base_df['PlanEnd'] <= t_cut_plan]
print(f"\n仓面 with PlanEnd <= t_cut_plan: {len(before_cut)}")

after_cut = base_df[base_df['PlanEnd'] > t_cut_plan]
print(f"仓面 with PlanEnd > t_cut_plan: {len(after_cut)}")

a_ids = set(f"{int(row['DamID'])}-{int(row['LayerID'])}" for _, row in act_df.iterrows())
before_not_a = before_cut[~before_cut.apply(lambda r: f"{int(r['DamID'])}-{int(r['LayerID'])}" in a_ids, axis=1)]
print(f"Before t_cut_plan but not in A: {len(before_not_a)}")
if len(before_not_a) > 0:
    for _, row in before_not_a.iterrows():
        print(f"  {int(row['DamID'])}-{int(row['LayerID'])}: PlanEnd={row['PlanEnd'].strftime('%Y/%m/%d')}")

print(f"\n=== After t_cut_plan sorted by PlanEnd (first 30) ===")
after_sorted = after_cut.sort_values('PlanEnd')
for i, (_, row) in enumerate(after_sorted.head(30).iterrows()):
    wid = f"{int(row['DamID'])}-{int(row['LayerID'])}"
    print(f"  {i+1}. {wid}: PlanEnd={row['PlanEnd'].strftime('%Y/%m/%d')}")
