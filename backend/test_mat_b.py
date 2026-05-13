import pandas as pd
import os

mat_dir = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\输出结果\Run_20260314_235628'

comb_file = os.path.join(mat_dir, '完整排仓计划.xlsx')
comb = pd.read_excel(comb_file)

# Identify B segment: rows where 实际开始时间 > 计划开始时间 significantly
# A segment: rows where 实际开始时间 is in 2025
# B segment: rows where 实际开始时间 is in 2026/04-2026/05
# C segment: rows where 实际开始时间 is later

# From the output, A segment is rows 0-21, B segment starts at row 22
# Let's identify B segment by looking at the pattern
a_end = 22  # First B segment row

# Print rows 20-50 to see B and C segment boundary
print('=== MATLAB Rows 20-50 ===')
for i in range(20, min(50, len(comb))):
    row = comb.iloc[i]
    wid = row['编号']
    dam = row['坝段号']
    layer = row['仓号']
    plan_end = row['计划结束时间']
    plan_start = row['计划开始时间']
    actual_start = row['实际开始时间']
    actual_end = row['实际结束时间']
    print(f'Row {i}: {wid} PlanEnd={plan_start}~{plan_end} Actual={actual_start}~{actual_end}')

# Now let's also check the MATLAB WarehouseData for crane count and rest time
print()
mat_wh_file = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\WarehouseData.xlsx'
mat_wh = pd.read_excel(mat_wh_file)
print('=== MATLAB WarehouseData (crane count & rest time) ===')
print('Columns:', list(mat_wh.columns))
for i, row in mat_wh.iterrows():
    wid = row.iloc[0]
    crane = row.iloc[7] if len(row) > 7 else '?'
    rest = row.iloc[8] if len(row) > 8 else '?'
    print(f'  {wid}: crane={crane}, rest={rest}')
