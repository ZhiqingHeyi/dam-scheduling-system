"""
AIWARE 数据库 API 接口
提供对 aiware 数据库的 RESTful API 访问
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
import pandas as pd

from aiware_db.connection import test_aiware_connection, init_aiware_database, AIWAREDBConfig
from aiware_db.repository import (
    SchedulingRunRepository, WarehouseScheduleRepository,
    MonthlyPlanRepository, SchedulingWeightRepository, SystemConfigRepository
)
from aiware_db.sync_service import AIWARESyncService, get_scheduling_result, get_latest_runs
from aiware_db.models import RunStatus, RunType, Segment, WindowType

router = APIRouter(prefix="/api/aiware", tags=["AIWARE数据库"])


# ==================== Pydantic 模型 ====================

class DBConfigRequest(BaseModel):
    host: str = Field(default="192.168.1.88", description="数据库主机")
    port: int = Field(default=3306, description="数据库端口")
    user: str = Field(default="root", description="用户名")
    password: str = Field(default="!Tmhc20170717", description="密码")
    database: str = Field(default="aiware", description="数据库名")


class SchedulingRunResponse(BaseModel):
    id: Optional[int]
    run_id: str
    run_name: Optional[str]
    run_type: str
    start_date: Optional[date]
    deadline_date: Optional[date]
    actual_end_date: Optional[date]
    alpha: float
    total_warehouses: int
    count_a: int
    count_b: int
    count_c: int
    status: str
    progress_percent: int
    created_at: Optional[datetime]
    created_by: Optional[str]


class WarehouseScheduleResponse(BaseModel):
    id: Optional[int]
    run_id: str
    warehouse_id: str
    dam_id: int
    layer_id: int
    segment: str
    segment_order: Optional[int]
    top_elevation: Optional[float]
    bottom_elevation: Optional[float]
    plan_start_date: Optional[date]
    plan_end_date: Optional[date]
    actual_start_date: Optional[date]
    actual_end_date: Optional[date]
    final_start_date: Optional[date]
    final_end_date: Optional[date]
    status: str
    score: Optional[float]
    priority_rank: Optional[int]
    pouring_volume: Optional[float]
    crane_count: int
    rest_days: Optional[float]
    pouring_intensity: Optional[float]


class MonthlyPlanResponse(BaseModel):
    id: Optional[int]
    run_id: str
    window_type: str
    window_name: Optional[str]
    window_start_date: Optional[date]
    window_end_date: Optional[date]
    warehouse_count: int
    count_a: int
    count_b: int
    count_c: int
    file_path: Optional[str]
    file_name: Optional[str]
    created_at: Optional[datetime]


class SchedulingWeightResponse(BaseModel):
    id: Optional[int]
    run_id: str
    indicator_name: str
    indicator_index: Optional[int]
    ahp_weight: Optional[float]
    entropy_weight: Optional[float]
    combined_weight: Optional[float]
    is_benefit: bool
    cr_value: Optional[float]


class SchedulingResultResponse(BaseModel):
    run: SchedulingRunResponse
    warehouses: List[WarehouseScheduleResponse]
    weights: List[SchedulingWeightResponse]
    monthly_plans: List[MonthlyPlanResponse]


class SyncResultRequest(BaseModel):
    run_id: str
    run_name: str
    start_date: date
    deadline_date: Optional[date] = None
    alpha: float = 0.5
    created_by: Optional[str] = None


# ==================== API 路由 ====================

@router.post("/test-connection", summary="测试数据库连接")
async def test_connection(config: Optional[DBConfigRequest] = None):
    """测试AIWARE数据库连接"""
    try:
        if config:
            # 使用自定义配置
            db_config = AIWAREDBConfig(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database
            )
            from aiware_db.connection import AIWAREConnection
            AIWAREConnection.set_config(db_config)
        
        success = test_aiware_connection()
        if success:
            return {"success": True, "message": "数据库连接成功"}
        else:
            return {"success": False, "message": "数据库连接失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接测试失败: {str(e)}")


@router.post("/init-database", summary="初始化数据库")
async def init_database(config: Optional[DBConfigRequest] = None):
    """初始化AIWARE数据库（创建表结构）"""
    try:
        if config:
            db_config = AIWAREDBConfig(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database
            )
            from aiware_db.connection import AIWAREConnection
            AIWAREConnection.set_config(db_config)
        
        success = init_aiware_database()
        if success:
            return {"success": True, "message": "数据库初始化成功"}
        else:
            return {"success": False, "message": "数据库初始化失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")


@router.get("/runs", summary="获取运行记录列表", response_model=List[SchedulingRunResponse])
async def get_runs(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    """获取排仓运行记录列表"""
    try:
        with SchedulingRunRepository() as repo:
            runs = repo.get_all(limit=limit, offset=offset)
            return [SchedulingRunResponse(**run.to_dict()) for run in runs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取运行记录失败: {str(e)}")


@router.get("/runs/latest", summary="获取最新运行记录", response_model=List[SchedulingRunResponse])
async def get_latest_runs_api(limit: int = Query(10, ge=1, le=100)):
    """获取最新的排仓运行记录"""
    try:
        runs = get_latest_runs(limit)
        return [SchedulingRunResponse(**run) for run in runs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最新记录失败: {str(e)}")


@router.get("/runs/{run_id}", summary="获取运行详情", response_model=SchedulingRunResponse)
async def get_run(run_id: str):
    """根据run_id获取运行记录详情"""
    try:
        with SchedulingRunRepository() as repo:
            run = repo.get_by_id(run_id)
            if not run:
                raise HTTPException(status_code=404, detail="运行记录不存在")
            return SchedulingRunResponse(**run.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取运行记录失败: {str(e)}")


@router.get("/runs/{run_id}/full", summary="获取完整排仓结果", response_model=SchedulingResultResponse)
async def get_full_result(run_id: str):
    """获取完整的排仓结果（包括仓面、权重、月计划）"""
    try:
        result = get_scheduling_result(run_id)
        if not result:
            raise HTTPException(status_code=404, detail="排仓结果不存在")
        
        return SchedulingResultResponse(
            run=SchedulingRunResponse(**result['run']),
            warehouses=[WarehouseScheduleResponse(**w) for w in result['warehouses']],
            weights=[SchedulingWeightResponse(**w) for w in result['weights']],
            monthly_plans=[MonthlyPlanResponse(**mp) for mp in result['monthly_plans']]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取排仓结果失败: {str(e)}")


@router.get("/runs/{run_id}/warehouses", summary="获取仓面计划列表", response_model=List[WarehouseScheduleResponse])
async def get_warehouses(run_id: str, segment: Optional[str] = None):
    """获取指定运行的仓面计划列表"""
    try:
        with WarehouseScheduleRepository() as repo:
            if segment:
                warehouses = repo.get_by_segment(run_id, Segment(segment))
            else:
                warehouses = repo.get_by_run_id(run_id)
            return [WarehouseScheduleResponse(**w.to_dict()) for w in warehouses]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仓面计划失败: {str(e)}")


@router.get("/runs/{run_id}/warehouses/by-date", summary="按日期范围获取仓面计划", response_model=List[WarehouseScheduleResponse])
async def get_warehouses_by_date(run_id: str, start_date: date, end_date: date):
    """根据日期范围获取仓面计划"""
    try:
        with AIWARESyncService() as service:
            warehouses = service.get_warehouse_schedule_by_date_range(run_id, start_date, end_date)
            return [WarehouseScheduleResponse(**w) for w in warehouses]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仓面计划失败: {str(e)}")


@router.get("/runs/{run_id}/monthly-plans", summary="获取月计划列表", response_model=List[MonthlyPlanResponse])
async def get_monthly_plans(run_id: str):
    """获取指定运行的月计划列表"""
    try:
        with MonthlyPlanRepository() as repo:
            plans = repo.get_by_run_id(run_id)
            return [MonthlyPlanResponse(**mp.to_dict()) for mp in plans]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取月计划失败: {str(e)}")


@router.get("/runs/{run_id}/weights", summary="获取权重配置", response_model=List[SchedulingWeightResponse])
async def get_weights(run_id: str):
    """获取指定运行的权重配置"""
    try:
        with SchedulingWeightRepository() as repo:
            weights = repo.get_by_run_id(run_id)
            return [SchedulingWeightResponse(**w.to_dict()) for w in weights]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取权重配置失败: {str(e)}")


@router.delete("/runs/{run_id}", summary="删除运行记录")
async def delete_run(run_id: str):
    """删除指定的运行记录及其关联数据"""
    try:
        with SchedulingRunRepository() as repo:
            success = repo.delete(run_id)
            if success:
                return {"success": True, "message": f"运行记录 {run_id} 已删除"}
            else:
                raise HTTPException(status_code=404, detail="运行记录不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除运行记录失败: {str(e)}")


@router.get("/config/{key}", summary="获取系统配置")
async def get_config(key: str):
    """获取系统配置值"""
    try:
        with SystemConfigRepository() as repo:
            config = repo.get(key)
            if config:
                return {
                    "key": config.config_key,
                    "value": config.get_typed_value(),
                    "type": config.config_type,
                    "description": config.description
                }
            else:
                raise HTTPException(status_code=404, detail="配置不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.get("/config", summary="获取所有系统配置")
async def get_all_configs():
    """获取所有系统配置"""
    try:
        with SystemConfigRepository() as repo:
            configs = repo.get_all()
            return [
                {
                    "key": c.config_key,
                    "value": c.get_typed_value(),
                    "type": c.config_type,
                    "description": c.description
                }
                for c in configs
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/config/{key}", summary="设置系统配置")
async def set_config(key: str, value: str, config_type: str = "string", description: str = None):
    """设置系统配置值"""
    try:
        with SystemConfigRepository() as repo:
            repo.set(key, value, config_type, description)
            return {"success": True, "message": f"配置 {key} 已设置"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置配置失败: {str(e)}")


@router.get("/stats/summary", summary="获取统计摘要")
async def get_stats_summary():
    """获取AIWARE数据库统计摘要"""
    try:
        stats = {}
        
        # 运行记录统计
        with SchedulingRunRepository() as run_repo:
            runs = run_repo.get_all(limit=10000)
            stats['total_runs'] = len(runs)
            stats['completed_runs'] = len([r for r in runs if r.status == RunStatus.COMPLETED])
            stats['failed_runs'] = len([r for r in runs if r.status == RunStatus.FAILED])
            stats['total_warehouses'] = sum(r.total_warehouses for r in runs)
        
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")
