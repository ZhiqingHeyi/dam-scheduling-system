import pandas as pd

mat_filled = pd.read_excel(r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\WarehouseData_filled.xlsx')
print(f"MATLAB WarehouseData_filled: {mat_filled.shape}")
print(f"Columns: {list(mat_filled.columns)}")
print(f"First 5 rows:")
print(mat_filled.head(5).to_string())

mat_wh = pd.read_excel(r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\WarehouseData.xlsx')
print(f"\nMATLAB WarehouseData (B段): {mat_wh.shape}")
print(f"Columns: {list(mat_wh.columns)}")
print(f"First 5 rows:")
print(mat_wh.head(5).to_string())

our_filled = pd.read_excel('./uploads/WarehouseData_filled.xlsx')
print(f"\nOur WarehouseData_filled: {our_filled.shape}")
print(f"Columns: {list(our_filled.columns)}")
print(f"First 5 rows:")
print(our_filled.head(5).to_string())

mat_filled_ids = mat_filled.iloc[:, 0].astype(str).tolist()
our_filled_ids = our_filled.iloc[:, 0].astype(str).tolist()

mat_wh_ids = mat_wh.iloc[:, 0].astype(str).tolist()

print(f"\nMATLAB WarehouseData IDs (B段): {mat_wh_ids}")
print(f"\nMATLAB filled IDs in our filled: {set(mat_filled_ids) & set(our_filled_ids)}")
print(f"MATLAB filled IDs NOT in our filled: {set(mat_filled_ids) - set(our_filled_ids)}")
print(f"Our filled IDs NOT in MATLAB filled: {set(our_filled_ids) - set(mat_filled_ids)}")

print(f"\nMATLAB B段 IDs in our filled: {set(mat_wh_ids) & set(our_filled_ids)}")
print(f"MATLAB B段 IDs NOT in our filled: {set(mat_wh_ids) - set(our_filled_ids)}")
