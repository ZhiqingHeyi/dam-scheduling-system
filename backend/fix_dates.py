import pandas as pd
import os

upload_dir = 'uploads'

base_file = os.path.join(upload_dir, 'BaselineSchedule.xlsx')
if os.path.exists(base_file):
    df = pd.read_excel(base_file)
    for col in ['PlanStart', 'PlanEnd']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]) - pd.Timedelta(days=1)
    df.to_excel(base_file, index=False)
    first_ps = df['PlanStart'].iloc[0]
    print(f'BaselineSchedule: subtracted 1 day, first PlanStart = {first_ps}')

actual_file = os.path.join(upload_dir, 'ActualDone.xlsx')
if os.path.exists(actual_file):
    df = pd.read_excel(actual_file)
    for col in ['ActualStart', 'ActualEnd']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]) - pd.Timedelta(days=1)
    df.to_excel(actual_file, index=False)
    if len(df) > 0:
        first_as = df['ActualStart'].iloc[0]
        print(f'ActualDone: subtracted 1 day, first ActualStart = {first_as}')
