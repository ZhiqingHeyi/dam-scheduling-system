"""
AIWARE 数据库模块
拱坝智能排仓计划数据存储系统

提供以下功能:
- 数据库连接管理
- 排仓运行记录存储
- 仓面计划详情存储
- 月计划窗口管理
- 权重配置存储
- 数据查询接口
"""

from .connection import get_aiware_connection, AIWAREDBConfig
from .models import (
    SchedulingRun,
    WarehouseSchedule,
    MonthlyPlan,
    SchedulingWeight,
    SystemConfig
)
from .repository import (
    SchedulingRunRepository,
    WarehouseScheduleRepository,
    MonthlyPlanRepository,
    SchedulingWeightRepository,
    SystemConfigRepository
)
from .sync_service import AIWARESyncService

__all__ = [
    # 连接
    'get_aiware_connection',
    'AIWAREDBConfig',
    # 模型
    'SchedulingRun',
    'WarehouseSchedule',
    'MonthlyPlan',
    'SchedulingWeight',
    'SystemConfig',
    # 仓储
    'SchedulingRunRepository',
    'WarehouseScheduleRepository',
    'MonthlyPlanRepository',
    'SchedulingWeightRepository',
    'SystemConfigRepository',
    # 服务
    'AIWARESyncService',
]

__version__ = '1.0.0'
