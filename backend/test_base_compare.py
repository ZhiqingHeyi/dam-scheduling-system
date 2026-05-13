import pandas as pd
import numpy as np
import os

base_file = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\BaselineSchedule.xlsx'
mat_base = pd.read_excel(base_file, header=None, skiprows=2)
print(f"MATLAB BaselineSchedule raw: {mat_base.shape}")
print(f"First 5 rows:")
print(mat_base.head(5).to_string())

mat_base.columns = ['idx', 'DamID', 'LayerID', 'PlanStart', 'PlanEnd', 'col5', 'col6', 'col7', 'TopElev'] + [f'col{i}' for i in range(9, len(mat_base.columns))]
print(f"\nDamID sample: {mat_base['DamID'].head(10).tolist()}")
print(f"LayerID sample: {mat_base['LayerID'].head(10).tolist()}")
print(f"PlanStart sample: {mat_base['PlanStart'].head(10).tolist()}")
print(f"PlanEnd sample: {mat_base['PlanEnd'].head(10).tolist()}")
print(f"TopElev sample: {mat_base['TopElev'].head(10).tolist()}")

valid = mat_base.dropna(subset=['DamID', 'LayerID', 'PlanStart', 'PlanEnd'])
print(f"\nValid rows: {len(valid)}")

mat_base_ours = pd.read_excel('./uploads/BaselineSchedule.xlsx')
print(f"\nOur BaselineSchedule: {len(mat_base_ours)} rows")
print(f"Columns: {list(mat_base_ours.columns)}")

if len(valid) == len(mat_base_ours):
    print("Row count matches!")
else:
    print(f"Row count MISMATCH: MATLAB={len(valid)}, Python={len(mat_base_ours)}")

for i in range(min(5, len(mat_base_ours))):
    our_dam = int(mat_base_ours.iloc[i]['DamID'])
    our_layer = int(mat_base_ours.iloc[i]['LayerID'])
    our_pe = pd.Timestamp(mat_base_ours.iloc[i]['PlanEnd']).strftime('%Y/%m/%d')
    
    mat_dam = valid.iloc[i]['DamID']
    mat_layer = valid.iloc[i]['LayerID']
    mat_pe = valid.iloc[i]['PlanEnd']
    
    print(f"  Row {i}: Python={our_dam}-{our_layer} PlanEnd={our_pe}, MATLAB={mat_dam}-{mat_layer} PlanEnd={mat_pe}")
