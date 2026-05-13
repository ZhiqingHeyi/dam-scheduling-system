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

a, b, c, t, b1, b2 = split_schedule_abc(base_df, act_df, 10)
print(f'A={len(a)}, B={len(b)}, C={len(c)}')
print(f'B1={len(b1)}, B2={len(b2)}')
b_ids = [f"{int(base_df.iloc[i]['DamID'])}-{int(base_df.iloc[i]['LayerID'])}" for i in b]
print(f'B IDs: {b_ids}')

b1_ids = [f"{int(base_df.iloc[i]['DamID'])}-{int(base_df.iloc[i]['LayerID'])}" for i in b1]
print(f'B1 IDs: {b1_ids}')

b2_ids = [f"{int(base_df.iloc[i]['DamID'])}-{int(base_df.iloc[i]['LayerID'])}" for i in b2]
print(f'B2 IDs: {b2_ids}')

print(f'\nt_cut_plan = {t}')

mat_wh_ids = ['15-3', '19-5', '17-6', '21-1', '16-5', '18-4', '20-5', '17-7', '19-6', '16-6',
              '15-7', '17-7', '19-7', '21-1', '14-2', '16-5', '18-5', '21-2', '15-8', '17-8',
              '19-8', '14-3', '16-6', '18-6', '21-3', '17-9', '19-9', '14-4', '16-7', '18-7',
              '20-6', '13-1', '15-9', '17-10', '19-10', '19-11', '21-4', '16-8', '18-8', '13-2',
              '20-7', '17-11', '21-5', '13-3', '20-8', '18-9', '15-10', '21-6', '17-12', '19-12',
              '14-5', '22-1', '16-9']
print(f'\nMATLAB WarehouseData IDs ({len(mat_wh_ids)}): {mat_wh_ids}')
print(f'Python B IDs in MATLAB: {set(b_ids) & set(mat_wh_ids)}')
print(f'MATLAB IDs not in Python B: {set(mat_wh_ids) - set(b_ids)}')
