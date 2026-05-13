# AIWARE 数据库模块

拱坝智能排仓计划数据存储系统 - 独立于现有 qbt 数据库的新模块

## 📁 模块结构

```
aiware_db/
├── __init__.py              # 模块初始化
├── connection.py            # 数据库连接管理
├── models.py                # 数据模型定义
├── repository.py            # 数据仓储层 (CRUD)
├── sync_service.py          # 数据同步服务
├── example_usage.py         # 使用示例
└── README.md               # 本文档
```

## 🗄️ 数据库设计

### 数据库信息
- **数据库名**: `aiware`
- **主机**: `192.168.1.88:3306`
- **字符集**: `utf8mb4`

### 表结构

#### 1. scheduling_runs (排仓运行记录主表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| run_id | VARCHAR(50) | 运行标识 (如: Run_20260427_091850) |
| run_name | VARCHAR(200) | 运行名称 |
| run_type | ENUM | 运行类型 (normal/compress/manual) |
| start_date | DATE | 排仓开始日期 |
| deadline_date | DATE | 工期截止日期 |
| actual_end_date | DATE | 实际完成日期 |
| alpha | DECIMAL(3,2) | AHP权重系数 |
| total_warehouses | INT | 总仓面数 |
| count_a/b/c | INT | A/B/C段数量 |
| status | ENUM | 运行状态 |
| created_at | TIMESTAMP | 创建时间 |

#### 2. warehouse_schedules (仓面计划详情表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| run_id | VARCHAR(50) | 关联运行ID |
| warehouse_id | VARCHAR(50) | 仓面编号 (如: 15-23) |
| dam_id | INT | 坝段号 |
| layer_id | INT | 层号 |
| segment | ENUM | ABC分段 |
| top_elevation | DECIMAL(10,2) | 仓顶高程(m) |
| plan_start/end_date | DATE | 计划起止日期 |
| final_start/end_date | DATE | 最终排仓起止日期 |
| score | DECIMAL(10,6) | 综合得分 |
| status | ENUM | 仓面状态 |

#### 3. monthly_plans (月计划窗口表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| run_id | VARCHAR(50) | 关联运行ID |
| window_type | ENUM | 窗口类型 (fixed/next/rolling) |
| window_start/end_date | DATE | 窗口起止日期 |
| warehouse_count | INT | 仓面数量 |
| file_path | VARCHAR(500) | 导出文件路径 |

#### 4. scheduling_weights (权重配置表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| run_id | VARCHAR(50) | 关联运行ID |
| indicator_name | VARCHAR(50) | 指标名称 |
| ahp_weight | DECIMAL(8,6) | AHP权重 |
| entropy_weight | DECIMAL(8,6) | 熵权法权重 |
| combined_weight | DECIMAL(8,6) | 组合权重 |
| cr_value | DECIMAL(6,4) | 一致性比率 |

#### 5. system_configs (系统配置表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| config_key | VARCHAR(100) | 配置键 |
| config_value | TEXT | 配置值 |
| config_type | VARCHAR(20) | 值类型 |

## 🚀 快速开始

### 1. 初始化数据库

```python
from aiware_db.connection import init_aiware_database

# 创建数据库和表
init_aiware_database()
```

或执行SQL脚本:
```bash
mysql -u root -p < sql/create_aiware_tables.sql
```

### 2. 保存排仓结果

```python
from aiware_db.sync_service import save_scheduling_result
from datetime import date
import pandas as pd

# 保存排仓结果
save_scheduling_result(
    run_id="Run_20260427_091850",
    run_name="4月排仓计划",
    start_date=date(2026, 4, 27),
    deadline_date=date(2026, 12, 31),
    alpha=0.5,
    t_all=df,  # 排仓结果DataFrame
    weights={
        'ahp_weights': [0.25, 0.20, 0.18, 0.15, 0.12, 0.10],
        'entropy_weights': [...],
        'combined_weights': [...]
    },
    plan_windows={
        'fixed_count': 10,
        'fixed_window_start': '2026-04-01',
        'fixed_window_end': '2026-04-30',
        ...
    },
    created_by="admin"
)
```

### 3. 查询排仓结果

```python
from aiware_db.sync_service import get_scheduling_result

# 获取完整排仓结果
result = get_scheduling_result("Run_20260427_091850")

print(result['run'])           # 运行记录
print(result['warehouses'])    # 仓面计划列表
print(result['weights'])       # 权重配置
```

### 4. 使用仓储层

```python
from aiware_db.repository import SchedulingRunRepository, WarehouseScheduleRepository
from aiware_db.models import Segment

# 查询运行记录
with SchedulingRunRepository() as repo:
    runs = repo.get_latest(limit=10)
    for run in runs:
        print(f"{run.run_id}: {run.run_name}")

# 查询仓面
with WarehouseScheduleRepository() as repo:
    # 获取所有B段仓面
    b_warehouses = repo.get_by_segment("Run_20260427_091850", Segment.B)
    
    # 按日期范围查询
    warehouses = repo.get_by_date_range(
        "Run_20260427_091850",
        date(2026, 4, 1),
        date(2026, 4, 30)
    )
```

## 📡 API 接口

启动服务后，访问 `http://localhost:8000/docs` 查看完整API文档

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/aiware/init-database` | 初始化数据库 |
| GET | `/api/aiware/runs` | 获取运行记录列表 |
| GET | `/api/aiware/runs/{run_id}` | 获取运行详情 |
| GET | `/api/aiware/runs/{run_id}/full` | 获取完整排仓结果 |
| GET | `/api/aiware/runs/{run_id}/warehouses` | 获取仓面计划 |
| GET | `/api/aiware/runs/{run_id}/monthly-plans` | 获取月计划 |
| DELETE | `/api/aiware/runs/{run_id}` | 删除运行记录 |
| GET | `/api/aiware/config` | 获取系统配置 |
| GET | `/api/aiware/stats/summary` | 获取统计摘要 |

## 🔧 配置说明

### 数据库配置

编辑 `aiware_db/connection.py` 修改默认配置:

```python
@dataclass
class AIWAREDBConfig:
    host: str = "192.168.1.88"
    port: int = 3306
    user: str = "root"
    password: str = "!Tmhc20170717"
    database: str = "aiware"
```

### 系统配置

使用 `system_configs` 表存储全局配置:

```python
from aiware_db.repository import SystemConfigRepository

with SystemConfigRepository() as repo:
    # 设置配置
    repo.set('scheduling.alpha', '0.6', 'float', 'AHP权重系数')
    
    # 获取配置
    alpha = repo.get_value('scheduling.alpha', default=0.5)
```

## 📊 与现有系统的集成

### 在排仓计算后保存结果

修改 `api/scheduling.py` 中的 `run_scheduling_pipeline` 函数:

```python
from aiware_db.sync_service import save_scheduling_result
from datetime import date

async def run_scheduling_pipeline(request, progress_callback=None):
    # ... 原有排仓逻辑 ...
    
    # 保存结果到AIWARE数据库
    run_result = save_output_files(t_all, request)
    run_id = run_result['run_id']
    
    # 同步到AIWARE
    save_scheduling_result(
        run_id=run_id,
        run_name=f"排仓计划 {run_id}",
        start_date=datetime.strptime(request.start_date, '%Y/%m/%d').date(),
        deadline_date=datetime.strptime(request.deadline_date, '%Y/%m/%d').date() if request.deadline_date else None,
        alpha=request.alpha,
        t_all=t_all,
        weights={
            'ahp_weights': ahp_weights.tolist(),
            'entropy_weights': entropy_weights.tolist(),
            'combined_weights': combined_weights.tolist(),
            'cr': float(cr)
        },
        plan_windows=plan_files_info,
        created_by="system"
    )
    
    return result
```

## 📝 注意事项

1. **数据库权限**: 确保MySQL用户有创建数据库和表的权限
2. **字符集**: 使用 `utf8mb4` 支持完整Unicode字符
3. **事务管理**: 仓储层自动处理事务提交/回滚
4. **日期处理**: 所有日期字段使用Python `date` 对象
5. **外键约束**: 使用级联删除，删除运行记录会同时删除关联数据

## 🔍 调试和测试

运行示例程序:

```bash
cd dam-scheduling-system/backend
python aiware_db/example_usage.py
```

这将执行以下操作:
1. 测试数据库连接
2. 初始化数据库表
3. 保存示例排仓结果
4. 查询并显示结果
5. 导出到Excel

## 📚 依赖项

```
pymysql
pandas
numpy
```

已在 `requirements.txt` 中包含。

---

**版本**: 1.0.0  
**创建日期**: 2026-05-03
