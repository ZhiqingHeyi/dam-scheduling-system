import pandas as pd
import numpy as np

test_dir = 'output/test_run_v2'
mat_dir = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\输出结果\Run_20260314_235628'

py_df = pd.read_excel(test_dir + '/完整排仓计划.xlsx')
mat_df = pd.read_excel(mat_dir + '/完整排仓计划.xlsx')

print('=== B段仓面对比 (Row 19-38) ===')
for i in range(19, min(40, len(py_df), len(mat_df))):
    py_id = str(py_df.iloc[i]['编号'])
    mat_id = str(mat_df.iloc[i]['编号'])
    py_fs = str(py_df.iloc[i]['实际开始时间'])
    mat_fs = str(mat_df.iloc[i]['实际开始时间'])
    py_ps = str(py_df.iloc[i]['计划开始时间'])
    mat_ps = str(mat_df.iloc[i]['计划开始时间'])
    match = '✓' if py_id == mat_id and py_fs == mat_fs else '✗'
    print(f'Row {i}: Python={py_id} (计划={py_ps}, 实际={py_fs}) | MATLAB={mat_id} (计划={mat_ps}, 实际={mat_fs}) {match}')

print()
print('=== 按编号匹配对比 ===')
py_dict = {}
for i in range(len(py_df)):
    py_dict[str(py_df.iloc[i]['编号'])] = i

mat_dict = {}
for i in range(len(mat_df)):
    mat_dict[str(mat_df.iloc[i]['编号'])] = i

b_ids = ['15-3', '15-4', '19-5', '21-1', '21-2', '17-5', '16-4', '18-4', '20-4', '19-6']
for bid in b_ids:
    if bid in py_dict and bid in mat_dict:
        py_i = py_dict[bid]
        mat_i = mat_dict[bid]
        py_fs = str(py_df.iloc[py_i]['实际开始时间'])
        mat_fs = str(mat_df.iloc[mat_i]['实际开始时间'])
        py_fe = str(py_df.iloc[py_i]['实际结束时间'])
        mat_fe = str(mat_df.iloc[mat_i]['实际结束时间'])
        match = '✓' if py_fs == mat_fs else '✗'
        print(f'{bid}: Python[Row{py_i}] 实际={py_fs}~{py_fe} | MATLAB[Row{mat_i}] 实际={mat_fs}~{mat_fe} {match}')
