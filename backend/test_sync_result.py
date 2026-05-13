import pandas as pd
df = pd.read_excel('./uploads/BaselineSchedule.xlsx')
print(f'Rows: {len(df)}')
print(f'Unique DamID+LayerID: {len(df.drop_duplicates(subset=["DamID","LayerID"]))}')
for c in ['PlanStart', 'PlanEnd']:
    df[c] = pd.to_datetime(df[c])
print(f'First 3 rows:')
print(df.head(3).to_string())
print(f'\nLast 3 rows:')
print(df.tail(3).to_string())

act_df = pd.read_excel('./uploads/ActualDone.xlsx')
for c in ['ActualStart', 'ActualEnd']:
    act_df[c] = pd.to_datetime(act_df[c])
print(f'\nActualDone: {len(act_df)} rows')
print(f'First 3:')
print(act_df.head(3).to_string())

from api.scheduling import split_schedule_abc
a_idx, b_idx, c_idx, t_cut_plan, b1_idx, b2_idx = split_schedule_abc(df, act_df, 10)
print(f'\nA={len(a_idx)}, B={len(b_idx)}, C={len(c_idx)}')
print(f'B1={len(b1_idx)}, B2={len(b2_idx)}')
print(f't_cut_plan={t_cut_plan}')

b_ids = [f"{int(df.iloc[i]['DamID'])}-{int(df.iloc[i]['LayerID'])}" for i in b_idx]
print(f'B IDs: {b_ids}')

b1_ids = [f"{int(df.iloc[i]['DamID'])}-{int(df.iloc[i]['LayerID'])}" for i in b1_idx]
print(f'B1 IDs: {b1_ids}')

b2_ids = [f"{int(df.iloc[i]['DamID'])}-{int(df.iloc[i]['LayerID'])}" for i in b2_idx]
print(f'B2 IDs: {b2_ids}')
