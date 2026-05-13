"""
AIWARE 数据同步服务
将排仓计算结果同步到AIWARE数据库
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import os

from .connection import get_aiware_connection
from .models import (
    SchedulingRun, WarehouseSchedule, MonthlyPlan, SchedulingWeight,
    RunStatus, RunType, Segment, WindowType, WarehouseStatus
)
from .repository import (
    SchedulingRunRepository, WarehouseScheduleRepository,
    MonthlyPlanRepository, SchedulingWeightRepository
)


class AIWARESyncService:
    """AIWARE数据同步服务"""
    
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
    
    def save_scheduling_result(self, 
                               run_id: str,
                               run_name: str,
                               start_date: date,
                               deadline_date: Optional[date],
                               alpha: float,
                               t_all: pd.DataFrame,
                               weights: Dict[str, List[float]],
                               plan_windows: Dict[str, Any],
                               created_by: str = None) -> bool:
        """
        保存排仓计算结果到AIWARE数据库
        
        Args:
            run_id: 运行标识
            run_name: 运行名称
            start_date: 排仓开始日期
            deadline_date: 截止日期
            alpha: AHP权重系数
            t_all: 完整排仓计划DataFrame
            weights: 权重字典 {ahp_weights, entropy_weights, combined_weights}
            plan_windows: 计划窗口信息
            created_by: 创建用户
        
        Returns:
            bool: 是否成功
        """
        try:
            # 1. 创建运行记录
            run = self._create_run_record(
                run_id, run_name, start_date, deadline_date, alpha, t_all, created_by
            )
            
            with SchedulingRunRepository() as run_repo:
                run_repo.create(run)
            
            # 2. 保存仓面计划
            self._save_warehouse_schedules(run_id, t_all)
            
            # 3. 保存权重配置
            if weights:
                self._save_weights(run_id, weights)
            
            # 4. 保存月计划窗口
            if plan_windows:
                self._save_monthly_plans(run_id, plan_windows)
            
            # 5. 更新运行状态为完成
            with SchedulingRunRepository() as run_repo:
                run_repo.update_status(run_id, RunStatus.COMPLETED, 100)
            
            print(f"排仓结果已保存到AIWARE数据库: {run_id}")
            return True
            
        except Exception as e:
            print(f"保存排仓结果失败: {e}")
            # 更新状态为失败
            try:
                with SchedulingRunRepository() as run_repo:
                    run_repo.update_status(run_id, RunStatus.FAILED)
            except:
                pass
            raise
    
    def _create_run_record(self, 
                          run_id: str,
                          run_name: str,
                          start_date: date,
                          deadline_date: Optional[date],
                          alpha: float,
                          t_all: pd.DataFrame,
                          created_by: str = None) -> SchedulingRun:
        """创建运行记录"""
        # 统计各段数量
        count_a = len(t_all[t_all['Segment'] == 'A']) if 'Segment' in t_all.columns else 0
        count_b = len(t_all[t_all['Segment'] == 'B']) if 'Segment' in t_all.columns else 0
        count_c = len(t_all[t_all['Segment'] == 'C']) if 'Segment' in t_all.columns else 0
        
        # 获取实际完成日期
        actual_end = None
        if count_a > 0 and 'FinalEnd' in t_all.columns:
            a_data = t_all[t_all['Segment'] == 'A']
            if len(a_data) > 0:
                actual_end = pd.to_datetime(a_data['FinalEnd'].max()).date()
        
        return SchedulingRun(
            run_id=run_id,
            run_name=run_name,
            run_type=RunType.NORMAL,
            start_date=start_date,
            deadline_date=deadline_date,
            actual_end_date=actual_end,
            alpha=alpha,
            max_crane_per_day=4,
            min_gap_days=7,
            max_gap_days=20,
            n_extra=10,
            total_warehouses=len(t_all),
            count_a=count_a,
            count_b=count_b,
            count_c=count_c,
            status=RunStatus.RUNNING,
            progress_percent=0,
            created_by=created_by
        )
    
    def _save_warehouse_schedules(self, run_id: str, t_all: pd.DataFrame):
        """保存仓面计划"""
        warehouses = []

        elev_lookup = {}
        if 'TopElev' in t_all.columns:
            for _, r in t_all.iterrows():
                d = int(r.get('DamID', 0)) if not pd.isna(r.get('DamID')) else None
                l = int(r.get('LayerID', 0)) if not pd.isna(r.get('LayerID')) else None
                e = r.get('TopElev')
                if d is not None and l is not None and not pd.isna(e):
                    elev_lookup[(d, l)] = float(e)

        for idx, row in t_all.iterrows():
            warehouse_id = str(row.get('WarehouseID', ''))
            if '-' in warehouse_id:
                parts = warehouse_id.split('-')
                dam_id = int(parts[0]) if parts[0].isdigit() else 0
                layer_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            else:
                dam_id = int(row.get('DamID', 0))
                layer_id = int(row.get('LayerID', 0))
                warehouse_id = f"{dam_id}-{layer_id}"

            segment_str = str(row.get('Segment', 'C'))
            segment = Segment(segment_str) if segment_str in ['A', 'B', 'C'] else Segment.C

            def parse_date(val):
                if pd.isna(val):
                    return None
                try:
                    dt = pd.to_datetime(val)
                    return dt.date()
                except:
                    return None

            top_elev_val = float(row.get('TopElev')) if 'TopElev' in row and not pd.isna(row.get('TopElev')) else None
            bottom_elev_val = None
            if top_elev_val is not None:
                prev_key = (dam_id, layer_id - 1)
                if prev_key in elev_lookup:
                    bottom_elev_val = elev_lookup[prev_key]
                else:
                    dam_elevs = {lid: elev for (did, lid), elev in elev_lookup.items() if did == dam_id and lid < layer_id}
                    if dam_elevs:
                        bottom_elev_val = dam_elevs[max(dam_elevs.keys())]
                    else:
                        bottom_elev_val = top_elev_val - 3
            
            # 创建仓面记录
            ws = WarehouseSchedule(
                run_id=run_id,
                warehouse_id=warehouse_id,
                dam_id=dam_id,
                layer_id=layer_id,
                segment=segment,
                segment_order=idx,
                top_elevation=top_elev_val,
                bottom_elevation=bottom_elev_val,
                plan_start_date=parse_date(row.get('PlanStart')),
                plan_end_date=parse_date(row.get('PlanEnd')),
                actual_start_date=parse_date(row.get('ActualStart')),
                actual_end_date=parse_date(row.get('ActualEnd')),
                final_start_date=parse_date(row.get('FinalStart')),
                final_end_date=parse_date(row.get('FinalEnd')),
                status=WarehouseStatus.COMPLETED if segment == Segment.A else WarehouseStatus.PLANNED,
                score=float(row.get('Score')) if 'Score' in row and not pd.isna(row.get('Score')) else None,
                priority_rank=idx,
                pouring_volume=None,
                crane_count=1,
                rest_days=None,
                pouring_intensity=None
            )
            warehouses.append(ws)
        
        # 批量保存
        with WarehouseScheduleRepository() as ws_repo:
            ws_repo.create_many(warehouses)
        
        print(f"已保存 {len(warehouses)} 个仓面计划")
    
    def _save_weights(self, run_id: str, weights: Dict[str, List[float]]):
        """保存权重配置"""
        weight_records = []
        
        indicator_names = ['坝段高程', '奇偶坝段', '孔口坝段', '浇筑方量', '顶块间歇', '浇筑强度']
        
        ahp_weights = weights.get('ahp_weights', [])
        entropy_weights = weights.get('entropy_weights', [])
        combined_weights = weights.get('combined_weights', [])
        cr_value = weights.get('cr', None)
        
        for i, name in enumerate(indicator_names):
            weight = SchedulingWeight(
                run_id=run_id,
                indicator_name=name,
                indicator_index=i,
                ahp_weight=ahp_weights[i] if i < len(ahp_weights) else None,
                entropy_weight=entropy_weights[i] if i < len(entropy_weights) else None,
                combined_weight=combined_weights[i] if i < len(combined_weights) else None,
                is_benefit=True if i != 4 else False,  # 第5个指标(顶块间歇)是负向指标
                cr_value=cr_value if i == 0 else None  # 只在第一条记录存CR值
            )
            weight_records.append(weight)
        
        with SchedulingWeightRepository() as weight_repo:
            weight_repo.create_many(weight_records)
        
        print(f"已保存 {len(weight_records)} 个权重配置")
    
    def _save_monthly_plans(self, run_id: str, plan_windows: Dict[str, Any]):
        """保存月计划窗口"""
        monthly_plans = []
        
        # 固定周期月计划
        if 'fixed_window_start' in plan_windows and 'fixed_window_end' in plan_windows:
            mp = MonthlyPlan(
                run_id=run_id,
                window_type=WindowType.FIXED,
                window_name='固定周期月计划',
                window_start_date=pd.to_datetime(plan_windows['fixed_window_start']).date(),
                window_end_date=pd.to_datetime(plan_windows['fixed_window_end']).date(),
                warehouse_count=plan_windows.get('fixed_count', 0),
                file_path=plan_windows.get('fixed'),
                file_name=os.path.basename(plan_windows.get('fixed', '')) if plan_windows.get('fixed') else None
            )
            monthly_plans.append(mp)
        
        # 下月度月计划
        if 'next_month_window_start' in plan_windows and 'next_month_window_end' in plan_windows:
            mp = MonthlyPlan(
                run_id=run_id,
                window_type=WindowType.NEXT,
                window_name='下月度月计划',
                window_start_date=pd.to_datetime(plan_windows['next_month_window_start']).date(),
                window_end_date=pd.to_datetime(plan_windows['next_month_window_end']).date(),
                warehouse_count=plan_windows.get('next_month_count', 0),
                file_path=plan_windows.get('nextMonth'),
                file_name=os.path.basename(plan_windows.get('nextMonth', '')) if plan_windows.get('nextMonth') else None
            )
            monthly_plans.append(mp)
        
        # 滚动周期月计划
        if 'rolling_window_start' in plan_windows and 'rolling_window_end' in plan_windows:
            mp = MonthlyPlan(
                run_id=run_id,
                window_type=WindowType.ROLLING,
                window_name='滚动周期月计划',
                window_start_date=pd.to_datetime(plan_windows['rolling_window_start']).date(),
                window_end_date=pd.to_datetime(plan_windows['rolling_window_end']).date(),
                warehouse_count=plan_windows.get('rolling_count', 0),
                file_path=plan_windows.get('rolling'),
                file_name=os.path.basename(plan_windows.get('rolling', '')) if plan_windows.get('rolling') else None
            )
            monthly_plans.append(mp)
        
        with MonthlyPlanRepository() as mp_repo:
            for mp in monthly_plans:
                mp_repo.create(mp)
        
        print(f"已保存 {len(monthly_plans)} 个月计划窗口")
    
    def get_scheduling_result(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        从AIWARE数据库获取排仓结果
        
        Args:
            run_id: 运行标识
        
        Returns:
            Dict: 包含运行记录、仓面计划、权重等信息的字典
        """
        result = {}
        
        # 获取运行记录
        with SchedulingRunRepository() as run_repo:
            run = run_repo.get_by_id(run_id)
            if not run:
                return None
            result['run'] = run.to_dict()
        
        # 获取仓面计划
        with WarehouseScheduleRepository() as ws_repo:
            warehouses = ws_repo.get_by_run_id(run_id)
            result['warehouses'] = [w.to_dict() for w in warehouses]
        
        # 获取权重
        with SchedulingWeightRepository() as weight_repo:
            weights = weight_repo.get_by_run_id(run_id)
            result['weights'] = [w.to_dict() for w in weights]
        
        # 获取月计划
        with MonthlyPlanRepository() as mp_repo:
            monthly_plans = mp_repo.get_by_run_id(run_id)
            result['monthly_plans'] = [mp.to_dict() for mp in monthly_plans]
        
        return result
    
    def get_latest_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最新的运行记录"""
        with SchedulingRunRepository() as run_repo:
            runs = run_repo.get_latest(limit)
            return [run.to_dict() for run in runs]
    
    def get_warehouse_schedule_by_date_range(self, 
                                              run_id: str, 
                                              start_date: date, 
                                              end_date: date) -> List[Dict[str, Any]]:
        """根据日期范围获取仓面计划"""
        with WarehouseScheduleRepository() as ws_repo:
            warehouses = ws_repo.get_by_date_range(run_id, start_date, end_date)
            return [w.to_dict() for w in warehouses]
    
    def export_to_dataframe(self, run_id: str) -> pd.DataFrame:
        """将排仓结果导出为DataFrame"""
        result = self.get_scheduling_result(run_id)
        if not result or 'warehouses' not in result:
            return pd.DataFrame()
        
        return pd.DataFrame(result['warehouses'])


# 便捷函数
def save_scheduling_result(run_id: str,
                          run_name: str,
                          start_date: date,
                          deadline_date: Optional[date],
                          alpha: float,
                          t_all: pd.DataFrame,
                          weights: Dict[str, List[float]],
                          plan_windows: Dict[str, Any],
                          created_by: str = None) -> bool:
    """保存排仓结果的便捷函数"""
    with AIWARESyncService() as service:
        return service.save_scheduling_result(
            run_id, run_name, start_date, deadline_date, alpha,
            t_all, weights, plan_windows, created_by
        )


def get_scheduling_result(run_id: str) -> Optional[Dict[str, Any]]:
    """获取排仓结果的便捷函数"""
    with AIWARESyncService() as service:
        return service.get_scheduling_result(run_id)


def get_latest_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """获取最新运行记录的便捷函数"""
    with AIWARESyncService() as service:
        return service.get_latest_runs(limit)
