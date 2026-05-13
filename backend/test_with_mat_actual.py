import pandas as pd
import sys
import os
sys.path.insert(0, '.')
from api.scheduling import split_schedule_abc

mat_act_file = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\ActualDone.xlsx'
mat_act = pd.read_excel(mat_act_file, header=None, skiprows=2)
mat_act.columns = ['DamID', 'LayerID', 'ActualStart', 'ActualEnd']
mat_act['ActualStart'] = pd.to_datetime(mat_act['ActualStart']) + pd.Timedelta(days=1)
mat_act['ActualEnd'] = pd.to_datetime(mat_act['ActualEnd']) + pd.Timedelta(days=1)

print(f"MATLAB ActualDone: {len(mat_act)} records")
for _, r in mat_act.iterrows():
    print(f"  {int(r['DamID'])}-{int(r['LayerID'])}: {r['ActualStart'].strftime('%Y-%m-%d')} ~ {r['ActualEnd'].strftime('%Y-%m-%d')}")

mat_act.to_excel('./uploads/ActualDone.xlsx', index=False)
print(f"\nSaved MATLAB ActualDone to uploads/ActualDone.xlsx")

base_df = pd.read_excel('./uploads/BaselineSchedule.xlsx')
for c in ['PlanStart', 'PlanEnd']:
    base_df[c] = pd.to_datetime(base_df[c])

print(f"\nBaselineSchedule: {len(base_df)} records")

a_idx, b_idx, c_idx, t_cut_plan, b1_idx, b2_idx = split_schedule_abc(base_df, mat_act, 10)
print(f"\nsplit_schedule_abc results:")
print(f"  A={len(a_idx)}, B={len(b_idx)}, C={len(c_idx)}")
print(f"  B1={len(b1_idx)}, B2={len(b2_idx)}")
print(f"  t_cut_plan={t_cut_plan}")

b_ids = [f"{int(base_df.iloc[i]['DamID'])}-{int(base_df.iloc[i]['LayerID'])}" for i in b_idx]
b1_ids = [f"{int(base_df.iloc[i]['DamID'])}-{int(base_df.iloc[i]['LayerID'])}" for i in b1_idx]
b2_ids = [f"{int(base_df.iloc[i]['DamID'])}-{int(base_df.iloc[i]['LayerID'])}" for i in b2_idx]

print(f"  B1 IDs ({len(b1_ids)}): {b1_ids}")
print(f"  B2 IDs ({len(b2_ids)}): {b2_ids}")
print(f"  B IDs ({len(b_ids)}): {b_ids}")

matlab_b_ids = ['15-3', '19-5', '17-6', '21-1', '16-5', '18-4', '20-5', '17-7', '19-6', '16-6',
                '15-7', '17-7', '19-7', '21-1', '14-2', '16-5', '18-5', '21-2', '15-8', '17-8',
                '19-8', '14-3', '16-6', '18-6', '21-3', '17-9', '19-9', '14-4', '16-7', '18-7',
                '20-6', '13-1', '15-9', '17-10', '19-10', '19-11', '21-4', '16-8', '18-8', '13-2',
                '20-7', '17-11', '21-5', '13-3', '20-8', '18-9', '15-10', '21-6', '17-12', '19-12',
                '14-5', '22-1', '16-9']
matlab_b_set = set(matlab_b_ids)
our_b_set = set(b_ids)

print(f"\nMATLAB B segment: {len(matlab_b_set)} unique IDs")
print(f"Our B segment: {len(our_b_set)} unique IDs")
print(f"In MATLAB but not ours: {sorted(matlab_b_set - our_b_set)}")
print(f"In ours but not MATLAB: {sorted(our_b_set - matlab_b_set)}")
