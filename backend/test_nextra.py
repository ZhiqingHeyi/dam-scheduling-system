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

# Test with N_extra=10 (MATLAB default)
a_idx_10, b_idx_10, c_idx_10, t_cut_10, b1_idx_10, b2_idx_10 = split_schedule_abc(base_df, act_df, 10)
print('N_extra=10: A=%d, B=%d, C=%d' % (len(a_idx_10), len(b_idx_10), len(c_idx_10)))
print('  B1=%d, B2=%d' % (len(b1_idx_10), len(b2_idx_10)))
print('  B IDs:', get_ids(base_df, b_idx_10))

# Test with N_extra=20 (Python current)
a_idx_20, b_idx_20, c_idx_20, t_cut_20, b1_idx_20, b2_idx_20 = split_schedule_abc(base_df, act_df, 20)
print('\nN_extra=20: A=%d, B=%d, C=%d' % (len(a_idx_20), len(b_idx_20), len(c_idx_20)))
print('  B1=%d, B2=%d' % (len(b1_idx_20), len(b2_idx_20)))
print('  B IDs:', get_ids(base_df, b_idx_20))

# MATLAB's WarehouseData IDs
mat_ids = ['15-3', '19-5', '17-6', '21-1', '16-5', '18-4', '20-5', '17-7', '19-6', '16-6',
           '15-7', '17-7', '19-7', '21-1', '14-2', '16-5', '18-5', '21-2', '15-8', '17-8',
           '19-8', '14-3', '16-6', '18-6', '21-3', '17-9', '19-9', '14-4', '16-7', '18-7',
           '20-6', '13-1', '15-9', '17-10', '19-10', '19-11', '21-4', '16-8', '18-8', '13-2',
           '20-7', '17-11', '21-5', '13-3', '20-8', '18-9', '15-10', '21-6', '17-12', '19-12',
           '14-5', '22-1', '16-9']
print('\nMATLAB B段仓面数: %d' % len(mat_ids))

# Check if MATLAB's B段 IDs match Python's N_extra=10
py_ids_10 = get_ids(base_df, b_idx_10)
print('\nPython N_extra=10 B段 IDs:', py_ids_10)

# Check overlap
common_10 = set(py_ids_10) & set(mat_ids)
print('Common with MATLAB (N_extra=10): %d / %d' % (len(common_10), len(py_ids_10)))

# Try larger N_extra values
for ne in [30, 40, 50, 53]:
    a_idx, b_idx, c_idx, t_cut, b1_idx, b2_idx = split_schedule_abc(base_df, act_df, ne)
    py_ids = get_ids(base_df, b_idx)
    common = set(py_ids) & set(mat_ids)
    print('N_extra=%d: B=%d, common=%d/%d' % (ne, len(b_idx), len(common), len(mat_ids)))
