"""
AIWARE 数据仓储层
提供各模型的CRUD操作
"""
import pymysql
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from .connection import get_aiware_connection
from .models import (
    SchedulingRun, WarehouseSchedule, MonthlyPlan,
    SchedulingWeight, SystemConfig,
    RunStatus, RunType, Segment, WindowType, WarehouseStatus
)


class BaseRepository:
    """基础仓储类"""
    
    def __init__(self):
        self.connection = None
    
    def __enter__(self):
        self.connection = get_aiware_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            if exc_type:
                self.connection.rollback()
            else:
                self.connection.commit()
            self.connection.close()
        return False


class SchedulingRunRepository(BaseRepository):
    """排仓运行记录仓储"""
    
    TABLE_NAME = "scheduling_runs"
    
    def create(self, run: SchedulingRun) -> SchedulingRun:
        """创建运行记录"""
        sql = """
            INSERT INTO scheduling_runs (
                run_id, run_name, run_type, start_date, deadline_date,
                alpha, max_crane_per_day, min_gap_days, max_gap_days, n_extra,
                total_warehouses, count_a, count_b, count_c,
                status, progress_percent, created_by
            ) VALUES (
                %(run_id)s, %(run_name)s, %(run_type)s, %(start_date)s, %(deadline_date)s,
                %(alpha)s, %(max_crane_per_day)s, %(min_gap_days)s, %(max_gap_days)s, %(n_extra)s,
                %(total_warehouses)s, %(count_a)s, %(count_b)s, %(count_c)s,
                %(status)s, %(progress_percent)s, %(created_by)s
            )
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, self._to_dict(run))
            run.id = cursor.lastrowid
        return run
    
    def get_by_id(self, run_id: str) -> Optional[SchedulingRun]:
        """根据run_id获取记录"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE run_id = %(run_id)s"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {'run_id': run_id})
            row = cursor.fetchone()
            return self._from_dict(row) if row else None
    
    def get_by_run_id(self, run_id: str) -> Optional[SchedulingRun]:
        """根据run_id获取记录"""
        return self.get_by_id(run_id)
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[SchedulingRun]:
        """获取所有记录"""
        sql = f"SELECT * FROM {self.TABLE_NAME} ORDER BY created_at DESC LIMIT %(limit)s OFFSET %(offset)s"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {'limit': limit, 'offset': offset})
            rows = cursor.fetchall()
            return [self._from_dict(row) for row in rows]
    
    def update(self, run: SchedulingRun) -> bool:
        """更新运行记录"""
        sql = """
            UPDATE scheduling_runs SET
                run_name = %(run_name)s,
                status = %(status)s,
                progress_percent = %(progress_percent)s,
                total_warehouses = %(total_warehouses)s,
                count_a = %(count_a)s,
                count_b = %(count_b)s,
                count_c = %(count_c)s,
                actual_end_date = %(actual_end_date)s,
                completed_at = %(completed_at)s
            WHERE run_id = %(run_id)s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, self._to_dict(run))
            return cursor.rowcount > 0
    
    def update_status(self, run_id: str, status: RunStatus, progress: int = None) -> bool:
        """更新状态"""
        sql_parts = ["status = %(status)s"]
        params = {'run_id': run_id, 'status': status.value}
        
        if progress is not None:
            sql_parts.append("progress_percent = %(progress)s")
            params['progress'] = progress
        
        if status == RunStatus.COMPLETED:
            sql_parts.append("completed_at = NOW()")
        
        sql = f"UPDATE {self.TABLE_NAME} SET {', '.join(sql_parts)} WHERE run_id = %(run_id)s"
        
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0
    
    def delete(self, run_id: str) -> bool:
        """删除运行记录"""
        sql = f"DELETE FROM {self.TABLE_NAME} WHERE run_id = %(run_id)s"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {'run_id': run_id})
            return cursor.rowcount > 0
    
    def get_latest(self, limit: int = 10) -> List[SchedulingRun]:
        """获取最新的运行记录"""
        return self.get_all(limit=limit)
    
    def _to_dict(self, run: SchedulingRun) -> dict:
        """转换为字典"""
        return {
            'id': run.id,
            'run_id': run.run_id,
            'run_name': run.run_name,
            'run_type': run.run_type.value if run.run_type else RunType.NORMAL.value,
            'start_date': run.start_date,
            'deadline_date': run.deadline_date,
            'actual_end_date': run.actual_end_date,
            'alpha': run.alpha,
            'max_crane_per_day': run.max_crane_per_day,
            'min_gap_days': run.min_gap_days,
            'max_gap_days': run.max_gap_days,
            'n_extra': run.n_extra,
            'total_warehouses': run.total_warehouses,
            'count_a': run.count_a,
            'count_b': run.count_b,
            'count_c': run.count_c,
            'status': run.status.value if run.status else RunStatus.RUNNING.value,
            'progress_percent': run.progress_percent,
            'completed_at': run.completed_at,
            'created_by': run.created_by,
        }
    
    def _from_dict(self, row: dict) -> SchedulingRun:
        """从字典创建模型"""
        return SchedulingRun(
            id=row.get('id'),
            run_id=row.get('run_id'),
            run_name=row.get('run_name'),
            run_type=RunType(row.get('run_type', 'normal')),
            start_date=row.get('start_date'),
            deadline_date=row.get('deadline_date'),
            actual_end_date=row.get('actual_end_date'),
            alpha=row.get('alpha', 0.5),
            max_crane_per_day=row.get('max_crane_per_day', 4),
            min_gap_days=row.get('min_gap_days', 7),
            max_gap_days=row.get('max_gap_days', 20),
            n_extra=row.get('n_extra', 10),
            total_warehouses=row.get('total_warehouses', 0),
            count_a=row.get('count_a', 0),
            count_b=row.get('count_b', 0),
            count_c=row.get('count_c', 0),
            status=RunStatus(row.get('status', 'running')),
            progress_percent=row.get('progress_percent', 0),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            completed_at=row.get('completed_at'),
            created_by=row.get('created_by'),
        )


class WarehouseScheduleRepository(BaseRepository):
    """仓面计划详情仓储"""
    
    TABLE_NAME = "warehouse_schedules"
    
    def create(self, ws: WarehouseSchedule) -> WarehouseSchedule:
        """创建仓面计划"""
        sql = """
            INSERT INTO warehouse_schedules (
                run_id, warehouse_id, dam_id, layer_id,
                segment, segment_order, top_elevation, bottom_elevation,
                plan_start_date, plan_end_date,
                actual_start_date, actual_end_date, final_start_date, final_end_date,
                status, score, priority_rank,
                pouring_volume, crane_count, rest_days, pouring_intensity
            ) VALUES (
                %(run_id)s, %(warehouse_id)s, %(dam_id)s, %(layer_id)s,
                %(segment)s, %(segment_order)s, %(top_elevation)s, %(bottom_elevation)s,
                %(plan_start_date)s, %(plan_end_date)s,
                %(actual_start_date)s, %(actual_end_date)s, %(final_start_date)s, %(final_end_date)s,
                %(status)s, %(score)s, %(priority_rank)s,
                %(pouring_volume)s, %(crane_count)s, %(rest_days)s, %(pouring_intensity)s
            )
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, self._to_dict(ws))
            ws.id = cursor.lastrowid
        return ws
    
    def create_many(self, warehouses: List[WarehouseSchedule]) -> int:
        """批量创建仓面计划"""
        if not warehouses:
            return 0
        
        sql = """
            INSERT INTO warehouse_schedules (
                run_id, warehouse_id, dam_id, layer_id,
                segment, segment_order, top_elevation, bottom_elevation,
                plan_start_date, plan_end_date,
                actual_start_date, actual_end_date, final_start_date, final_end_date,
                status, score, priority_rank,
                pouring_volume, crane_count, rest_days, pouring_intensity
            ) VALUES (
                %(run_id)s, %(warehouse_id)s, %(dam_id)s, %(layer_id)s,
                %(segment)s, %(segment_order)s, %(top_elevation)s, %(bottom_elevation)s,
                %(plan_start_date)s, %(plan_end_date)s,
                %(actual_start_date)s, %(actual_end_date)s, %(final_start_date)s, %(final_end_date)s,
                %(status)s, %(score)s, %(priority_rank)s,
                %(pouring_volume)s, %(crane_count)s, %(rest_days)s, %(pouring_intensity)s
            )
        """
        with self.connection.cursor() as cursor:
            data = [self._to_dict(ws) for ws in warehouses]
            cursor.executemany(sql, data)
            return cursor.rowcount
    
    def get_by_run_id(self, run_id: str) -> List[WarehouseSchedule]:
        """根据run_id获取所有仓面"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE run_id = %(run_id)s ORDER BY segment, segment_order"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {'run_id': run_id})
            rows = cursor.fetchall()
            return [self._from_dict(row) for row in rows]
    
    def get_by_segment(self, run_id: str, segment: Segment) -> List[WarehouseSchedule]:
        """根据分段获取仓面"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE run_id = %(run_id)s AND segment = %(segment)s ORDER BY segment_order"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {'run_id': run_id, 'segment': segment.value})
            rows = cursor.fetchall()
            return [self._from_dict(row) for row in rows]
    
    def get_by_date_range(self, run_id: str, start_date: date, end_date: date) -> List[WarehouseSchedule]:
        """根据日期范围获取仓面"""
        sql = f"""
            SELECT * FROM {self.TABLE_NAME} 
            WHERE run_id = %(run_id)s 
            AND final_start_date <= %(end_date)s 
            AND final_end_date >= %(start_date)s
            ORDER BY final_start_date
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {'run_id': run_id, 'start_date': start_date, 'end_date': end_date})
            rows = cursor.fetchall()
            return [self._from_dict(row) for row in rows]
    
    def update(self, ws: WarehouseSchedule) -> bool:
        """更新仓面计划"""
        sql = """
            UPDATE warehouse_schedules SET
                final_start_date = %(final_start_date)s,
                final_end_date = %(final_end_date)s,
                status = %(status)s,
                score = %(score)s,
                priority_rank = %(priority_rank)s
            WHERE id = %(id)s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, self._to_dict(ws))
            return cursor.rowcount > 0
    
    def update_final_dates(self, run_id: str, warehouse_id: str, 
                          final_start: date, final_end: date) -> bool:
        """更新最终日期"""
        sql = f"""
            UPDATE {self.TABLE_NAME} 
            SET final_start_date = %(final_start)s, final_end_date = %(final_end)s
            WHERE run_id = %(run_id)s AND warehouse_id = %(warehouse_id)s
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {
                'run_id': run_id, 
                'warehouse_id': warehouse_id,
                'final_start': final_start,
                'final_end': final_end
            })
            return cursor.rowcount > 0
    
    def _to_dict(self, ws: WarehouseSchedule) -> dict:
        """转换为字典"""
        return {
            'id': ws.id,
            'run_id': ws.run_id,
            'warehouse_id': ws.warehouse_id,
            'dam_id': ws.dam_id,
            'layer_id': ws.layer_id,
            'segment': ws.segment.value if ws.segment else Segment.A.value,
            'segment_order': ws.segment_order,
            'top_elevation': ws.top_elevation,
            'bottom_elevation': ws.bottom_elevation,
            'plan_start_date': ws.plan_start_date,
            'plan_end_date': ws.plan_end_date,
            'actual_start_date': ws.actual_start_date,
            'actual_end_date': ws.actual_end_date,
            'final_start_date': ws.final_start_date,
            'final_end_date': ws.final_end_date,
            'status': ws.status.value if ws.status else WarehouseStatus.PLANNED.value,
            'score': ws.score,
            'priority_rank': ws.priority_rank,
            'pouring_volume': ws.pouring_volume,
            'crane_count': ws.crane_count,
            'rest_days': ws.rest_days,
            'pouring_intensity': ws.pouring_intensity,
        }
    
    def _from_dict(self, row: dict) -> WarehouseSchedule:
        """从字典创建模型"""
        return WarehouseSchedule(
            id=row.get('id'),
            run_id=row.get('run_id'),
            warehouse_id=row.get('warehouse_id'),
            dam_id=row.get('dam_id', 0),
            layer_id=row.get('layer_id', 0),
            segment=Segment(row.get('segment', 'A')),
            segment_order=row.get('segment_order'),
            top_elevation=row.get('top_elevation'),
            bottom_elevation=row.get('bottom_elevation'),
            plan_start_date=row.get('plan_start_date'),
            plan_end_date=row.get('plan_end_date'),
            actual_start_date=row.get('actual_start_date'),
            actual_end_date=row.get('actual_end_date'),
            final_start_date=row.get('final_start_date'),
            final_end_date=row.get('final_end_date'),
            status=WarehouseStatus(row.get('status', 'planned')),
            score=row.get('score'),
            priority_rank=row.get('priority_rank'),
            pouring_volume=row.get('pouring_volume'),
            crane_count=row.get('crane_count', 1),
            rest_days=row.get('rest_days'),
            pouring_intensity=row.get('pouring_intensity'),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )


class MonthlyPlanRepository(BaseRepository):
    """月计划窗口仓储"""
    
    TABLE_NAME = "monthly_plans"
    
    def create(self, mp: MonthlyPlan) -> MonthlyPlan:
        """创建月计划"""
        sql = """
            INSERT INTO monthly_plans (
                run_id, window_type, window_name,
                window_start_date, window_end_date,
                warehouse_count, count_a, count_b, count_c,
                file_path, file_name
            ) VALUES (
                %(run_id)s, %(window_type)s, %(window_name)s,
                %(window_start_date)s, %(window_end_date)s,
                %(warehouse_count)s, %(count_a)s, %(count_b)s, %(count_c)s,
                %(file_path)s, %(file_name)s
            )
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, self._to_dict(mp))
            mp.id = cursor.lastrowid
        return mp
    
    def get_by_run_id(self, run_id: str) -> List[MonthlyPlan]:
        """根据run_id获取所有月计划"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE run_id = %(run_id)s ORDER BY window_start_date"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {'run_id': run_id})
            rows = cursor.fetchall()
            return [self._from_dict(row) for row in rows]
    
    def get_by_type(self, run_id: str, window_type: WindowType) -> Optional[MonthlyPlan]:
        """根据类型获取月计划"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE run_id = %(run_id)s AND window_type = %(window_type)s LIMIT 1"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {'run_id': run_id, 'window_type': window_type.value})
            row = cursor.fetchone()
            return self._from_dict(row) if row else None
    
    def _to_dict(self, mp: MonthlyPlan) -> dict:
        """转换为字典"""
        return {
            'id': mp.id,
            'run_id': mp.run_id,
            'window_type': mp.window_type.value if mp.window_type else WindowType.FIXED.value,
            'window_name': mp.window_name,
            'window_start_date': mp.window_start_date,
            'window_end_date': mp.window_end_date,
            'warehouse_count': mp.warehouse_count,
            'count_a': mp.count_a,
            'count_b': mp.count_b,
            'count_c': mp.count_c,
            'file_path': mp.file_path,
            'file_name': mp.file_name,
        }
    
    def _from_dict(self, row: dict) -> MonthlyPlan:
        """从字典创建模型"""
        return MonthlyPlan(
            id=row.get('id'),
            run_id=row.get('run_id'),
            window_type=WindowType(row.get('window_type', 'fixed')),
            window_name=row.get('window_name'),
            window_start_date=row.get('window_start_date'),
            window_end_date=row.get('window_end_date'),
            warehouse_count=row.get('warehouse_count', 0),
            count_a=row.get('count_a', 0),
            count_b=row.get('count_b', 0),
            count_c=row.get('count_c', 0),
            file_path=row.get('file_path'),
            file_name=row.get('file_name'),
            created_at=row.get('created_at'),
        )


class SchedulingWeightRepository(BaseRepository):
    """权重配置仓储"""
    
    TABLE_NAME = "scheduling_weights"
    
    def create(self, weight: SchedulingWeight) -> SchedulingWeight:
        """创建权重记录"""
        sql = """
            INSERT INTO scheduling_weights (
                run_id, indicator_name, indicator_index,
                ahp_weight, entropy_weight, combined_weight,
                is_benefit, cr_value
            ) VALUES (
                %(run_id)s, %(indicator_name)s, %(indicator_index)s,
                %(ahp_weight)s, %(entropy_weight)s, %(combined_weight)s,
                %(is_benefit)s, %(cr_value)s
            )
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, self._to_dict(weight))
            weight.id = cursor.lastrowid
        return weight
    
    def create_many(self, weights: List[SchedulingWeight]) -> int:
        """批量创建权重记录"""
        if not weights:
            return 0
        
        sql = """
            INSERT INTO scheduling_weights (
                run_id, indicator_name, indicator_index,
                ahp_weight, entropy_weight, combined_weight,
                is_benefit, cr_value
            ) VALUES (
                %(run_id)s, %(indicator_name)s, %(indicator_index)s,
                %(ahp_weight)s, %(entropy_weight)s, %(combined_weight)s,
                %(is_benefit)s, %(cr_value)s
            )
        """
        with self.connection.cursor() as cursor:
            data = [self._to_dict(w) for w in weights]
            cursor.executemany(sql, data)
            return cursor.rowcount
    
    def get_by_run_id(self, run_id: str) -> List[SchedulingWeight]:
        """根据run_id获取所有权重"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE run_id = %(run_id)s ORDER BY indicator_index"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {'run_id': run_id})
            rows = cursor.fetchall()
            return [self._from_dict(row) for row in rows]
    
    def _to_dict(self, weight: SchedulingWeight) -> dict:
        """转换为字典"""
        return {
            'id': weight.id,
            'run_id': weight.run_id,
            'indicator_name': weight.indicator_name,
            'indicator_index': weight.indicator_index,
            'ahp_weight': weight.ahp_weight,
            'entropy_weight': weight.entropy_weight,
            'combined_weight': weight.combined_weight,
            'is_benefit': weight.is_benefit,
            'cr_value': weight.cr_value,
        }
    
    def _from_dict(self, row: dict) -> SchedulingWeight:
        """从字典创建模型"""
        return SchedulingWeight(
            id=row.get('id'),
            run_id=row.get('run_id'),
            indicator_name=row.get('indicator_name'),
            indicator_index=row.get('indicator_index'),
            ahp_weight=row.get('ahp_weight'),
            entropy_weight=row.get('entropy_weight'),
            combined_weight=row.get('combined_weight'),
            is_benefit=row.get('is_benefit', True),
            cr_value=row.get('cr_value'),
            created_at=row.get('created_at'),
        )


class SystemConfigRepository(BaseRepository):
    """系统配置仓储"""
    
    TABLE_NAME = "system_configs"
    
    def get(self, key: str) -> Optional[SystemConfig]:
        """根据key获取配置"""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE config_key = %(key)s"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {'key': key})
            row = cursor.fetchone()
            return self._from_dict(row) if row else None
    
    def get_value(self, key: str, default=None):
        """获取配置值"""
        config = self.get(key)
        if config:
            return config.get_typed_value()
        return default
    
    def get_all(self) -> List[SystemConfig]:
        """获取所有配置"""
        sql = f"SELECT * FROM {self.TABLE_NAME} ORDER BY config_key"
        with self.connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [self._from_dict(row) for row in rows]
    
    def set(self, key: str, value: Any, value_type: str = 'string', description: str = None) -> bool:
        """设置配置值"""
        sql = """
            INSERT INTO system_configs (config_key, config_value, config_type, description)
            VALUES (%(key)s, %(value)s, %(type)s, %(desc)s)
            ON DUPLICATE KEY UPDATE 
                config_value = %(value)s,
                config_type = %(type)s,
                description = COALESCE(%(desc)s, description)
        """
        with self.connection.cursor() as cursor:
            cursor.execute(sql, {
                'key': key,
                'value': str(value),
                'type': value_type,
                'desc': description
            })
            return True
    
    def _from_dict(self, row: dict) -> SystemConfig:
        """从字典创建模型"""
        return SystemConfig(
            id=row.get('id'),
            config_key=row.get('config_key'),
            config_value=row.get('config_value'),
            config_type=row.get('config_type', 'string'),
            description=row.get('description'),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )
