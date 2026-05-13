import pymysql
import pandas as pd
import os
from datetime import datetime, timedelta, date as date_type
from decimal import Decimal
import numpy as np

def safe_to_float(value):
    if value is None:
        return np.nan
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        if value == '' or value.lower() in ('null', 'nan', 'none', 'n/a'):
            return np.nan
        try:
            return float(value)
        except ValueError:
            try:
                cleaned = ''.join(c for c in value if c.isdigit() or c in '.-+')
                return float(cleaned) if cleaned else np.nan
            except ValueError:
                return np.nan
    try:
        return float(value)
    except (ValueError, TypeError):
        return np.nan

def parse_db_date(date_value):
    if date_value is None:
        return None
    if isinstance(date_value, datetime):
        return date_value.replace(hour=0, minute=0, second=0, microsecond=0)
    if isinstance(date_value, date_type) and not isinstance(date_value, datetime):
        return datetime(date_value.year, date_value.month, date_value.day)
    if isinstance(date_value, pd.Timestamp):
        return date_value.to_pydatetime().replace(hour=0, minute=0, second=0, microsecond=0)
    if isinstance(date_value, str):
        date_str = date_value.replace('T', ' ').strip()
        if date_str == '' or date_str.lower() in ('null', 'nan', 'none', 'n/a'):
            return None
        formats = ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
    if isinstance(date_value, (int, float, np.integer, np.floating)):
        try:
            if date_value > 30000 and date_value < 100000:
                epoch = datetime(1899, 12, 30) + timedelta(days=int(date_value))
                return epoch.replace(hour=0, minute=0, second=0, microsecond=0)
        except:
            pass
    return None

connection = pymysql.connect(
    host='192.168.1.88',
    port=3306,
    user='root',
    password='qbt123456',
    database='qbt',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

with connection.cursor() as cursor:
    sql_baseline = """
        SELECT 
            p.dam_section AS DamID,
            p.warehouse_number AS LayerID,
            p.start_time AS PlanStart,
            p.end_time AS PlanEnd,
            c.pouring_elevation AS TopElev
        FROM dam_pour p
        LEFT JOIN concreting_record c 
            ON p.dam_section = c.dam_section_no 
            AND p.warehouse_number = c.layer_no
        ORDER BY p.start_time, p.end_time, p.dam_section, p.warehouse_number
    """
    cursor.execute(sql_baseline)
    rows = cursor.fetchall()
    
    baseline_data = []
    for row in rows:
        try:
            dam_id = safe_to_float(row.get('DamID'))
            layer_id = safe_to_float(row.get('LayerID'))
            plan_start = parse_db_date(row.get('PlanStart'))
            plan_end = parse_db_date(row.get('PlanEnd'))
            top_elev = safe_to_float(row.get('TopElev'))
            
            if np.isnan(dam_id) or np.isnan(layer_id) or plan_start is None or plan_end is None:
                continue
            
            baseline_data.append({
                'DamID': int(dam_id),
                'LayerID': int(layer_id),
                'PlanStart': plan_start,
                'PlanEnd': plan_end,
                'TopElev': top_elev if not np.isnan(top_elev) else None
            })
        except:
            continue
    
    baseline_df = pd.DataFrame(baseline_data)
    baseline_df = baseline_df.sort_values(['PlanStart', 'PlanEnd', 'DamID', 'LayerID'])
    baseline_df = baseline_df.reset_index(drop=True)
    
    baseline_df.to_excel('uploads/BaselineSchedule.xlsx', index=False)
    print(f'Baseline: {len(baseline_df)} rows saved (no +1 day)')
    first_ps = baseline_df['PlanStart'].iloc[0]
    print(f'First PlanStart: {first_ps}')

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT 
            dam_segment_no AS DamID,
            layer_no AS LayerID,
            start_date AS ActualStart,
            end_date AS ActualEnd
        FROM ledger_pour_records
        ORDER BY end_date, start_date, dam_segment_no, layer_no
    """)
    actual_rows = cursor.fetchall()
    
    actual_data = []
    for row in actual_rows:
        try:
            d = safe_to_float(row.get('DamID'))
            l = safe_to_float(row.get('LayerID'))
            actual_start = parse_db_date(row.get('ActualStart'))
            actual_end = parse_db_date(row.get('ActualEnd'))
            
            if np.isnan(d) or np.isnan(l) or actual_start is None or actual_end is None:
                continue
            
            actual_data.append({
                'DamID': int(d),
                'LayerID': int(l),
                'ActualStart': actual_start,
                'ActualEnd': actual_end
            })
        except:
            continue
    
    actual_df = pd.DataFrame(actual_data)
    actual_df.to_excel('uploads/ActualDone.xlsx', index=False)
    print(f'Actual: {len(actual_df)} rows saved (no +1 day)')
    if len(actual_df) > 0:
        first_as = actual_df['ActualStart'].iloc[0]
        print(f'First ActualStart: {first_as}')

connection.close()
