"""
AIWARE 数据模型定义
使用dataclass定义数据库表对应的模型
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class RunStatus(str, Enum):
    """运行状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunType(str, Enum):
    """运行类型"""
    NORMAL = "normal"
    COMPRESS = "compress"
    MANUAL = "manual"


class Segment(str, Enum):
    """ABC分段"""
    A = "A"
    B = "B"
    C = "C"


class WindowType(str, Enum):
    """月计划窗口类型"""
    FIXED = "fixed"
    NEXT = "next"
    ROLLING = "rolling"


class WarehouseStatus(str, Enum):
    """仓面状态"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class SchedulingRun:
    """排仓运行记录模型"""
    id: Optional[int] = None
    run_id: str = ""  # 运行标识 (如: Run_20260427_091850)
    run_name: Optional[str] = None
    run_type: RunType = RunType.NORMAL
    
    # 时间参数
    start_date: Optional[date] = None
    deadline_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    
    # 算法参数
    alpha: float = 0.50
    max_crane_per_day: int = 4
    min_gap_days: int = 7
    max_gap_days: int = 20
    n_extra: int = 10
    
    # 统计信息
    total_warehouses: int = 0
    count_a: int = 0
    count_b: int = 0
    count_c: int = 0
    
    # 状态
    status: RunStatus = RunStatus.RUNNING
    progress_percent: int = 0
    
    # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 用户信息
    created_by: Optional[str] = None
    
    # 关联数据
    warehouses: List['WarehouseSchedule'] = field(default_factory=list)
    weights: List['SchedulingWeight'] = field(default_factory=list)
    monthly_plans: List['MonthlyPlan'] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'run_name': self.run_name,
            'run_type': self.run_type.value,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'deadline_date': self.deadline_date.isoformat() if self.deadline_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'alpha': self.alpha,
            'max_crane_per_day': self.max_crane_per_day,
            'min_gap_days': self.min_gap_days,
            'max_gap_days': self.max_gap_days,
            'n_extra': self.n_extra,
            'total_warehouses': self.total_warehouses,
            'count_a': self.count_a,
            'count_b': self.count_b,
            'count_c': self.count_c,
            'status': self.status.value,
            'progress_percent': self.progress_percent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_by': self.created_by,
        }


@dataclass
class WarehouseSchedule:
    """仓面计划详情模型"""
    id: Optional[int] = None
    run_id: str = ""
    
    # 仓面标识
    warehouse_id: str = ""  # 如: 15-23
    dam_id: int = 0
    layer_id: int = 0
    
    # 分段信息
    segment: Segment = Segment.A
    segment_order: Optional[int] = None
    
    # 高程信息
    top_elevation: Optional[float] = None
    bottom_elevation: Optional[float] = None
    
    # 计划时间
    plan_start_date: Optional[date] = None
    plan_end_date: Optional[date] = None
    
    # 实际/最终时间
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    final_start_date: Optional[date] = None
    final_end_date: Optional[date] = None
    
    # 状态
    status: WarehouseStatus = WarehouseStatus.PLANNED
    
    # 评分数据
    score: Optional[float] = None
    priority_rank: Optional[int] = None
    
    # 浇筑参数
    pouring_volume: Optional[float] = None
    crane_count: int = 1
    rest_days: Optional[float] = None
    pouring_intensity: Optional[float] = None
    
    # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'warehouse_id': self.warehouse_id,
            'dam_id': self.dam_id,
            'layer_id': self.layer_id,
            'segment': self.segment.value,
            'segment_order': self.segment_order,
            'top_elevation': self.top_elevation,
            'bottom_elevation': self.bottom_elevation,
            'plan_start_date': self.plan_start_date.isoformat() if self.plan_start_date else None,
            'plan_end_date': self.plan_end_date.isoformat() if self.plan_end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'final_start_date': self.final_start_date.isoformat() if self.final_start_date else None,
            'final_end_date': self.final_end_date.isoformat() if self.final_end_date else None,
            'status': self.status.value,
            'score': self.score,
            'priority_rank': self.priority_rank,
            'pouring_volume': self.pouring_volume,
            'crane_count': self.crane_count,
            'rest_days': self.rest_days,
            'pouring_intensity': self.pouring_intensity,
        }


@dataclass
class MonthlyPlan:
    """月计划窗口模型"""
    id: Optional[int] = None
    run_id: str = ""
    
    window_type: WindowType = WindowType.FIXED
    window_name: Optional[str] = None
    
    window_start_date: Optional[date] = None
    window_end_date: Optional[date] = None
    
    warehouse_count: int = 0
    count_a: int = 0
    count_b: int = 0
    count_c: int = 0
    
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    
    created_at: Optional[datetime] = None
    
    # 关联的仓面
    warehouses: List[WarehouseSchedule] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'window_type': self.window_type.value,
            'window_name': self.window_name,
            'window_start_date': self.window_start_date.isoformat() if self.window_start_date else None,
            'window_end_date': self.window_end_date.isoformat() if self.window_end_date else None,
            'warehouse_count': self.warehouse_count,
            'count_a': self.count_a,
            'count_b': self.count_b,
            'count_c': self.count_c,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class SchedulingWeight:
    """权重配置模型"""
    id: Optional[int] = None
    run_id: str = ""
    
    indicator_name: str = ""
    indicator_index: Optional[int] = None
    
    ahp_weight: Optional[float] = None
    entropy_weight: Optional[float] = None
    combined_weight: Optional[float] = None
    
    is_benefit: bool = True
    cr_value: Optional[float] = None
    
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'run_id': self.run_id,
            'indicator_name': self.indicator_name,
            'indicator_index': self.indicator_index,
            'ahp_weight': self.ahp_weight,
            'entropy_weight': self.entropy_weight,
            'combined_weight': self.combined_weight,
            'is_benefit': self.is_benefit,
            'cr_value': self.cr_value,
        }


@dataclass
class SystemConfig:
    """系统配置模型"""
    id: Optional[int] = None
    config_key: str = ""
    config_value: Optional[str] = None
    config_type: str = "string"
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'config_type': self.config_type,
            'description': self.description,
        }
    
    def get_typed_value(self):
        """根据类型返回转换后的值"""
        if self.config_value is None:
            return None
        
        if self.config_type == 'int':
            return int(self.config_value)
        elif self.config_type == 'float':
            return float(self.config_value)
        elif self.config_type == 'bool':
            return self.config_value.lower() in ('true', '1', 'yes', 'on')
        elif self.config_type == 'json':
            import json
            return json.loads(self.config_value)
        else:
            return self.config_value
