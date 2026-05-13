import pandas as pd
import numpy as np

test_dir = 'output/test_run_v2'
mat_dir = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\输出结果\Run_20260314_235628'

py_df = pd.read_excel(test_dir + '/完整排仓计划.xlsx')
mat_df = pd.read_excel(mat_dir + '/完整排仓计划.xlsx')

n_compare = min(len(py_df), len(mat_df))
diff_count = 0
first_diff = -1
for i in range(n_compare):
    py_row = py_df.iloc[i]
    mat_row = mat_df.iloc[i]
    diff = []
    for col in py_df.columns:
        if col in mat_df.columns:
            py_val = str(py_row[col])
            mat_val = str(mat_row[col])
            if py_val != mat_val:
                diff.append(f'{col}: Python={py_val}, MATLAB={mat_val}')
    if diff:
        diff_count += 1
        if first_diff < 0:
            first_diff = i
        if diff_count <= 30:
            print(f'Row {i} (编号={py_row["编号"]}): {diff}')

print(f'\n总差异行数: {diff_count}/{n_compare}')
print(f'第一个差异行: Row {first_diff}')
print(f'匹配率: {(n_compare - diff_count)/n_compare*100:.1f}%')

# Check the pattern of differences
if diff_count > 0:
    # Check if differences are only in certain columns
    col_diffs = {}
    for i in range(n_compare):
        py_row = py_df.iloc[i]
        mat_row = mat_df.iloc[i]
        for col in py_df.columns:
            if col in mat_df.columns:
                py_val = str(py_row[col])
                mat_val = str(mat_row[col])
                if py_val != mat_val:
                    col_diffs[col] = col_diffs.get(col, 0) + 1
    print(f'\n各列差异统计:')
    for col, count in sorted(col_diffs.items(), key=lambda x: -x[1]):
        print(f'  {col}: {count} 行不同')
