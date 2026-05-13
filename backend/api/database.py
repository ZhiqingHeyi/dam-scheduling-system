from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel
from typing import Optional
import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date as date_type
from decimal import Decimal
from config import settings
import json
import os
import traceback

router = APIRouter()

class DatabaseConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str

class TestConnectionResponse(BaseModel):
    success: bool
    message: str

@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_database_connection(config: DatabaseConfig):
    try:
        connection = pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            connect_timeout=5
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        
        connection.close()
        
        return TestConnectionResponse(
            success=True,
            message=f"数据库连接成功：{config.host}:{config.port} / {config.database}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库连接失败：{str(e)}")

def get_db_connection():
    return pymysql.connect(
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
        database=settings.DATABASE_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

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

@router.post("/sync-data")
async def sync_data_from_database(progress_callback=None):
    baseline_df = None
    baseline_file = os.path.join(settings.UPLOAD_DIR, 'BaselineSchedule.xlsx')
    
    async def notify(step, total, level, message):
        if progress_callback:
            try:
                await progress_callback(step, total, level, message)
            except TypeError:
                try:
                    await progress_callback(level, message)
                except:
                    pass
    
    try:
        await notify(1, 9, "INFO", "开始从数据库同步数据...")
        
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        connection = get_db_connection()
        
        try:
            with connection.cursor() as cursor:
                await notify(2, 9, "INFO", "正在读取基准计划数据（dam_pour + concreting_record）...")
                
                sql_baseline = """
                    SELECT 
                        p.dam_section AS DamID,
                        p.warehouse_number AS LayerID,
                        p.start_time AS PlanStart,
                        p.end_time AS PlanEnd,
                        c.pouring_elevation AS TopElev,
                        c.id AS RecordID,
                        c.crane AS Crane,
                        c.pouring_volume AS PouringVolume,
                        c.duration_time AS DurationTime
                    FROM dam_pour p
                    LEFT JOIN concreting_record c 
                        ON p.dam_section = c.dam_section_no 
                        AND p.warehouse_number = c.layer_no
                    ORDER BY p.start_time, p.end_time, p.dam_section, p.warehouse_number
                """
                
                cursor.execute(sql_baseline)
                rows = cursor.fetchall()
                
                if len(rows) == 0:
                    raise Exception("数据库中未找到基准计划数据（dam_pour表为空）")
                
                await notify(3, 9, "INFO", f"读取到 {len(rows)} 条原始记录，正在解析...")
                
                baseline_data = []
                parse_errors = 0
                for row in rows:
                    try:
                        dam_id = safe_to_float(row.get('DamID'))
                        layer_id = safe_to_float(row.get('LayerID'))
                        
                        plan_start = parse_db_date(row.get('PlanStart'))
                        plan_end = parse_db_date(row.get('PlanEnd'))
                        
                        if plan_start is not None:
                            plan_start = plan_start + timedelta(days=1)
                        if plan_end is not None:
                            plan_end = plan_end + timedelta(days=1)
                        
                        top_elev = safe_to_float(row.get('TopElev'))
                        
                        if np.isnan(dam_id) or np.isnan(layer_id) or plan_start is None or plan_end is None:
                            parse_errors += 1
                            continue
                        
                        baseline_data.append({
                            'DamID': int(dam_id),
                            'LayerID': int(layer_id),
                            'PlanStart': plan_start,
                            'PlanEnd': plan_end,
                            'TopElev': top_elev if not np.isnan(top_elev) else None
                        })
                    except Exception as e:
                        parse_errors += 1
                        continue
                
                if parse_errors > 0:
                    await notify(4, 9, "WARNING", f"解析警告：{parse_errors}/{len(rows)} 条记录解析失败")
                
                if len(baseline_data) == 0:
                    sample_row = rows[0] if rows else {}
                    sample_info = {k: f"{v}({type(v).__name__})" for k, v in sample_row.items()}
                    raise Exception(
                        f"解析基准计划数据失败，无有效记录。"
                        f"共{len(rows)}条原始记录，{parse_errors}条解析失败。"
                        f"样本数据：{json.dumps(sample_info, default=str, ensure_ascii=False)}"
                    )
                
                baseline_df = pd.DataFrame(baseline_data)
                if 'TopElev' in baseline_df.columns:
                    baseline_df['_elev_priority'] = baseline_df['TopElev'].notna().astype(int)
                    baseline_df = baseline_df.sort_values(['DamID', 'LayerID', '_elev_priority'], ascending=[True, True, False])
                    baseline_df = baseline_df.drop_duplicates(subset=['DamID', 'LayerID'], keep='first')
                    baseline_df = baseline_df.drop(columns=['_elev_priority'])
                else:
                    baseline_df = baseline_df.drop_duplicates(subset=['DamID', 'LayerID'], keep='first')
                baseline_df = baseline_df.sort_values(['PlanStart', 'PlanEnd', 'DamID', 'LayerID'])
                baseline_df = baseline_df.reset_index(drop=True)
                
                missing_elev = baseline_df['TopElev'].isna().sum()
                if missing_elev > 0:
                    await notify(4, 9, "INFO", f"有 {missing_elev} 条记录缺少高程数据，正在补全...")
                    elev_map = {}
                    
                    dam_elev_file = os.path.join(settings.UPLOAD_DIR, 'DamElevation.xlsx')
                    if os.path.exists(dam_elev_file):
                        try:
                            dam_elev_df = pd.read_excel(dam_elev_file)
                            for _, er in dam_elev_df.iterrows():
                                d = int(er['DamID']) if not pd.isna(er.get('DamID')) else None
                                l = int(er['LayerID']) if not pd.isna(er.get('LayerID')) else None
                                e = float(er['TopElev']) if not pd.isna(er.get('TopElev')) else None
                                if d is not None and l is not None and e is not None:
                                    elev_map[(d, l)] = e
                            await notify(4, 9, "INFO", f"从DamElevation.xlsx加载 {len(elev_map)} 条高程数据")
                        except Exception as e3:
                            await notify(4, 9, "WARNING", f"读取DamElevation.xlsx失败：{str(e3)}")
                    
                    if not elev_map:
                        try:
                            with connection.cursor() as cursor2:
                                cursor2.execute("SELECT dam_section, layer_no, top_elevation FROM dam_elevation")
                                elev_rows = cursor2.fetchall()
                                for er in elev_rows:
                                    ed = safe_to_float(er.get('dam_section', er.get('DamID')))
                                    el = safe_to_float(er.get('layer_no', er.get('LayerID')))
                                    ev = safe_to_float(er.get('top_elevation', er.get('TopElev')))
                                    if not np.isnan(ed) and not np.isnan(el) and not np.isnan(ev):
                                        elev_map[(int(ed), int(el))] = float(ev)
                                if elev_map:
                                    await notify(4, 9, "INFO", f"从dam_elevation表加载 {len(elev_map)} 条高程数据")
                        except Exception as e4:
                            await notify(4, 9, "INFO", f"dam_elevation表不存在或查询失败，尝试concreting_record...")
                    
                    if not elev_map:
                        try:
                            with connection.cursor() as cursor2:
                                cursor2.execute("""
                                    SELECT 
                                        dam_section_no AS DamID,
                                        layer_no AS LayerID,
                                        pouring_elevation AS TopElev
                                    FROM concreting_record
                                    WHERE pouring_elevation IS NOT NULL
                                """)
                                elev_rows = cursor2.fetchall()
                                for er in elev_rows:
                                    ed = safe_to_float(er.get('DamID'))
                                    el = safe_to_float(er.get('LayerID'))
                                    ev = safe_to_float(er.get('TopElev'))
                                    if not np.isnan(ed) and not np.isnan(el) and not np.isnan(ev):
                                        elev_map[(int(ed), int(el))] = float(ev)
                                if elev_map:
                                    await notify(4, 9, "INFO", f"从concreting_record加载 {len(elev_map)} 条高程数据")
                        except Exception as e2:
                            await notify(4, 9, "WARNING", f"高程补全查询失败：{str(e2)}")
                    
                    if elev_map:
                        filled = 0
                        for idx, row in baseline_df.iterrows():
                            if pd.isna(row.get('TopElev')):
                                key = (int(row['DamID']), int(row['LayerID']))
                                if key in elev_map:
                                    baseline_df.at[idx, 'TopElev'] = elev_map[key]
                                    filled += 1
                        still_missing = baseline_df['TopElev'].isna().sum()
                        await notify(4, 9, "INFO", f"高程补全：匹配 {filled} 条，仍有 {still_missing} 条缺失")
                
                baseline_df.to_excel(baseline_file, index=False)
                
                await notify(5, 9, "SUCCESS", f"基准计划同步完成：{len(baseline_df)} 条记录")
            
            with connection.cursor() as cursor:
                await notify(6, 9, "INFO", "正在读取实际完成数据（ledger_pour_records）...")
                
                try:
                    actual_data = []
                    seen_keys = set()
                    
                    cursor.execute("""
                        SELECT 
                            lpr.dam_segment_no AS DamID,
                            lpr.layer_no AS LayerID,
                            lpr.start_date AS ActualStart,
                            lpr.end_date AS ActualEnd,
                            lpr.id AS RecordID,
                            cr.pouring_elevation AS ActualTopElev
                        FROM ledger_pour_records lpr
                        LEFT JOIN concreting_record cr 
                            ON lpr.dam_segment_no = cr.dam_section_no 
                            AND lpr.layer_no = cr.layer_no
                        ORDER BY lpr.end_date, lpr.start_date, lpr.dam_segment_no, lpr.layer_no
                    """)
                    ledger_rows = cursor.fetchall()
                    
                    for row in ledger_rows:
                        try:
                            d = safe_to_float(row.get('DamID'))
                            l = safe_to_float(row.get('LayerID'))
                            actual_start = parse_db_date(row.get('ActualStart'))
                            actual_end = parse_db_date(row.get('ActualEnd'))
                            actual_top_elev = safe_to_float(row.get('ActualTopElev'))
                            
                            if actual_start is not None:
                                actual_start = actual_start + timedelta(days=1)
                            if actual_end is not None:
                                actual_end = actual_end + timedelta(days=1)
                            
                            if np.isnan(d) or np.isnan(l) or actual_start is None or actual_end is None:
                                continue
                            
                            key = (int(d), int(l))
                            if key not in seen_keys:
                                seen_keys.add(key)
                                record = {
                                    'DamID': int(d),
                                    'LayerID': int(l),
                                    'ActualStart': actual_start,
                                    'ActualEnd': actual_end
                                }
                            if not np.isnan(actual_top_elev):
                                record['ActualTopElev'] = float(actual_top_elev)
                            actual_data.append(record)
                        except:
                            continue
                    
                    if len(actual_data) > 0:
                        actual_df = pd.DataFrame(actual_data)
                        actual_df = actual_df.sort_values(['ActualEnd', 'ActualStart', 'DamID', 'LayerID'])
                        actual_df = actual_df.reset_index(drop=True)
                        actual_file = os.path.join(settings.UPLOAD_DIR, 'ActualDone.xlsx')
                        actual_df.to_excel(actual_file, index=False)
                        
                        await notify(7, 9, "SUCCESS", f"实际完成数据同步完成：{len(actual_df)} 条记录")
                    else:
                        await notify(7, 9, "INFO", "未找到有效的实际完成数据")
                        actual_file = os.path.join(settings.UPLOAD_DIR, 'ActualDone.xlsx')
                        if os.path.exists(actual_file):
                            os.remove(actual_file)
                
                except Exception as e:
                    await notify(7, 9, "WARNING", f"读取实际完成数据时出错：{str(e)}")
        
        finally:
            try:
                connection.close()
            except:
                pass
        
        warehouse_filled_file = os.path.join(settings.UPLOAD_DIR, 'WarehouseData_filled.xlsx')
        warehouse_file = os.path.join(settings.UPLOAD_DIR, 'WarehouseData.xlsx')
        
        if os.path.exists(warehouse_filled_file):
            await notify(8, 9, "INFO", "检测到本地仓面数据文件")
        elif os.path.exists(warehouse_file):
            await notify(8, 9, "INFO", "检测到基础仓面数据文件")
        else:
            await notify(8, 9, "WARNING", "未找到仓面数据文件，将使用模拟数据")
        
        ahp_file = os.path.join(settings.UPLOAD_DIR, 'AHPScores.xlsx')
        if os.path.exists(ahp_file):
            await notify(8, 9, "INFO", "检测到AHP评分文件")
        else:
            await notify(8, 9, "WARNING", "未找到AHP评分文件，将使用默认权重")
        
        await notify(9, 9, "SUCCESS", f"数据同步完成！输出目录：{settings.UPLOAD_DIR}")
        
        return {
            "success": True,
            "message": "数据同步成功",
            "details": {
                "baseline_records": len(baseline_df) if baseline_df is not None else 0,
                "baseline_file": baseline_file,
                "output_dir": settings.UPLOAD_DIR
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"数据同步失败：{str(e)}"
        try:
            await notify(9, 9, "ERROR", error_detail)
        except:
            pass
        raise HTTPException(status_code=500, detail=error_detail)

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
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y%m%d',
            '%d-%m-%Y',
            '%d/%m/%Y'
        ]
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

@router.get("/config")
async def get_database_config():
    return {
        "host": settings.DATABASE_HOST,
        "port": settings.DATABASE_PORT,
        "user": settings.DATABASE_USER,
        "password": settings.DATABASE_PASSWORD,
        "database": settings.DATABASE_NAME
    }

@router.post("/save-config")
async def save_database_config(config: DatabaseConfig):
    try:
        settings.DATABASE_HOST = config.host
        settings.DATABASE_PORT = config.port
        settings.DATABASE_USER = config.user
        settings.DATABASE_PASSWORD = config.password
        settings.DATABASE_NAME = config.database
        
        return {"success": True, "message": "数据库配置已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tables")
async def get_database_tables():
    try:
        connection = pymysql.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
        
        connection.close()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/query/{table_name}")
async def query_table(table_name: str, limit: int = 100):
    try:
        connection = pymysql.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
        
        connection.close()
        
        return {
            "table": table_name,
            "columns": columns,
            "data": rows,
            "count": len(rows)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
