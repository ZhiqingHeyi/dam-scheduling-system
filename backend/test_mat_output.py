import pandas as pd
import os

mat_dir = r'C:\Users\1\Desktop\智能建造实验室\拱坝动态规划-智能仓面排序模型\动态规划系统打包文件\2026.3.14\排序代码_最终版_2025.12.12_V48\V48build\输出结果\Run_20260314_235628'

comb_file = os.path.join(mat_dir, '完整排仓计划.xlsx')
comb = pd.read_excel(comb_file)
print('Columns:', list(comb.columns))
print('Total rows:', len(comb))

if 'Segment' in comb.columns:
    print('Segment values:', comb['Segment'].value_counts().to_dict())
    b_seg = comb[comb['Segment'] == 'B']
    print('B段仓面数:', len(b_seg))
    for _, row in b_seg.iterrows():
        wid = row.iloc[0]
        ps = row.get('PlanStart', '?')
        pe = row.get('PlanEnd', '?')
        fs = row.get('FinalStart', '?')
        fe = row.get('FinalEnd', '?')
        print(f'  {wid}: PlanStart={ps}, PlanEnd={pe}, FinalStart={fs}, FinalEnd={fe}')
else:
    print('No Segment column found')
    print('First 30 rows:')
    print(comb.head(30).to_string())
