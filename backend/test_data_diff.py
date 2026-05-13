import pandas as pd

base_df = pd.read_excel('./uploads/BaselineSchedule.xlsx')
print(f"BaselineSchedule: {len(base_df)} rows")

wh_df = pd.read_excel('./uploads/WarehouseData_filled.xlsx')
print(f"WarehouseData_filled: {len(wh_df)} rows")

base_ids = [f"{int(d)}-{int(l)}" for d, l in zip(base_df['DamID'], base_df['LayerID'])]
wh_ids = wh_df.iloc[:, 0].astype(str).tolist()

base_unique = set(base_ids)
wh_unique = set(wh_ids)

print(f"\nBaselineSchedule unique IDs: {len(base_unique)}")
print(f"WarehouseData_filled unique IDs: {len(wh_unique)}")

in_base_not_wh = base_unique - wh_unique
in_wh_not_base = wh_unique - base_unique

print(f"\nIn BaselineSchedule but not WarehouseData_filled: {len(in_base_not_wh)}")
if in_base_not_wh:
    print(f"  Sample: {list(in_base_not_wh)[:20]}")

print(f"\nIn WarehouseData_filled but not BaselineSchedule: {len(in_wh_not_base)}")
if in_wh_not_base:
    print(f"  Sample: {list(in_wh_not_base)[:20]}")

base_dupes = pd.Series(base_ids).value_counts()
base_dupes = base_dupes[base_dupes > 1]
print(f"\nDuplicate IDs in BaselineSchedule: {len(base_dupes)}")
if len(base_dupes) > 0:
    print(f"  {base_dupes.head(20).to_dict()}")

wh_dupes = pd.Series(wh_ids).value_counts()
wh_dupes = wh_dupes[wh_dupes > 1]
print(f"\nDuplicate IDs in WarehouseData_filled: {len(wh_dupes)}")
if len(wh_dupes) > 0:
    print(f"  {wh_dupes.head(20).to_dict()}")
