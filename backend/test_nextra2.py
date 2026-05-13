import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, '.')
from api.scheduling import split_schedule_abc

upload_dir = 'uploads'
base_file = os.path.join(upload_dir, 'BaselineSchedule.xlsx')
actual_file = os.path.join(upload_dir, 'ActualDone.xlsx')

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

def get_ids(base_df, idx_list):
    return [str(int(base_df.iloc[i]['DamID'])) + '-' + str(int(base_df.iloc[i]['LayerID'])) for i in idx_list]

# Test with N_extra=10
a_idx, b_idx, c_idx, t_cut, b1_idx, b2_idx = split_schedule_abc(base_df, act_df, 10)
print('N_extra=10:')
print('  A=%d, B=%d, C=%d' % (len(a_idx), len(b_idx), len(c_idx)))
print('  B1=%d, B2=%d' % (len(b1_idx), len(b2_idx)))
print('  B1 IDs:', get_ids(base_df, b1_idx))
print('  B2 IDs:', get_ids(base_df, b2_idx))
print('  t_cut_plan:', t_cut)

# Check the MATLAB complete schedule B segment IDs
mat_b_ids = ['15-3', '19-5', '20-5', '18-4', '19-6', '17-6', '16-5', '21-1', '17-7', '16-6',
             '21-2', '18-5', '15-4', '17-8', '19-7', '16-7', '14-1', '18-6', '20-6', '21-3']
print('\nMATLAB B段 IDs:', mat_b_ids)
print('MATLAB B段数量:', len(mat_b_ids))

# Check what N_extra gives us 20 B segment warehouses
for ne in range(10, 25):
    a_idx, b_idx, c_idx, t_cut, b1_idx, b2_idx = split_schedule_abc(base_df, act_df, ne)
    if len(b_idx) == 20:
        py_ids = get_ids(base_df, b_idx)
        print('\nN_extra=%d gives B=%d:' % (ne, len(b_idx)))
        print('  Python B IDs:', py_ids)
        mat_set = set(mat_b_ids)
        py_set = set(py_ids)
        print('  Common:', len(mat_set & py_set))
        print('  In MATLAB but not Python:', mat_set - py_set)
        print('  In Python but not MATLAB:', py_set - mat_set)
        break
