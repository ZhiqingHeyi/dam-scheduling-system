"""
AIWARE 数据库模块使用示例
展示如何保存和读取排仓结果
"""
import pandas as pd
import numpy as np
from datetime import datetime, date

# 导入AIWARE模块
from aiware_db.connection import test_aiware_connection, init_aiware_database
from aiware_db.sync_service import AIWARESyncService, save_scheduling_result, get_scheduling_result
from aiware_db.repository import (
    SchedulingRunRepository, WarehouseScheduleRepository,
    MonthlyPlanRepository, SchedulingWeightRepository
)
from aiware_db.models import RunStatus, Segment


def example_1_test_connection():
    """示例1: 测试数据库连接"""
    print("=" * 50)
    print("示例1: 测试数据库连接")
    print("=" * 50)
    
    success = test_aiware_connection()
    if success:
        print("✅ 数据库连接成功!")
    else:
        print("❌ 数据库连接失败!")
    return success


def example_2_init_database():
    """示例2: 初始化数据库"""
    print("\n" + "=" * 50)
    print("示例2: 初始化数据库")
    print("=" * 50)
    
    success = init_aiware_database()
    if success:
        print("✅ 数据库初始化成功!")
    else:
        print("❌ 数据库初始化失败!")
    return success


def example_3_save_scheduling_result():
    """示例3: 保存排仓结果"""
    print("\n" + "=" * 50)
    print("示例3: 保存排仓结果")
    print("=" * 50)
    
    # 创建模拟的排仓结果数据
    run_id = f"Run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 模拟 t_all DataFrame
    data = {
        'WarehouseID': ['15-1', '15-2', '15-3', '16-1', '16-2', '17-1'],
        'DamID': [15, 15, 15, 16, 16, 17],
        'LayerID': [1, 2, 3, 1, 2, 1],
        'Segment': ['A', 'A', 'B', 'A', 'B', 'C'],
        'TopElev': [993.0, 996.0, 999.0, 993.0, 996.0, 993.0],
        'PlanStart': pd.to_datetime(['2026-04-01', '2026-04-05', '2026-04-10', 
                                     '2026-04-02', '2026-04-08', '2026-04-15']),
        'PlanEnd': pd.to_datetime(['2026-04-02', '2026-04-06', '2026-04-11',
                                   '2026-04-03', '2026-04-09', '2026-04-16']),
        'FinalStart': pd.to_datetime(['2026-04-01', '2026-04-05', '2026-04-12',
                                      '2026-04-02', '2026-04-10', '2026-04-18']),
        'FinalEnd': pd.to_datetime(['2026-04-02', '2026-04-06', '2026-04-13',
                                    '2026-04-03', '2026-04-11', '2026-04-19']),
        'Score': [0.95, 0.92, 0.88, 0.90, 0.85, 0.82]
    }
    t_all = pd.DataFrame(data)
    
    # 权重数据
    weights = {
        'ahp_weights': [0.25, 0.20, 0.18, 0.15, 0.12, 0.10],
        'entropy_weights': [0.22, 0.21, 0.19, 0.16, 0.12, 0.10],
        'combined_weights': [0.235, 0.205, 0.185, 0.155, 0.12, 0.10],
        'cr': 0.05
    }
    
    # 计划窗口数据
    plan_windows = {
        'fixed': './output/月计划_固定周期.xlsx',
        'fixed_count': 3,
        'fixed_window_start': '2026-04-01',
        'fixed_window_end': '2026-04-30',
        'nextMonth': './output/月计划_下月度.xlsx',
        'next_month_count': 2,
        'next_month_window_start': '2026-05-01',
        'next_month_window_end': '2026-05-31',
        'rolling': './output/月计划_滚动周期.xlsx',
        'rolling_count': 4,
        'rolling_window_start': '2026-04-15',
        'rolling_window_end': '2026-05-14'
    }
    
    try:
        with AIWARESyncService() as service:
            success = service.save_scheduling_result(
                run_id=run_id,
                run_name="测试排仓运行",
                start_date=date(2026, 4, 1),
                deadline_date=date(2026, 12, 31),
                alpha=0.5,
                t_all=t_all,
                weights=weights,
                plan_windows=plan_windows,
                created_by="admin"
            )
        
        if success:
            print(f"✅ 排仓结果已保存: {run_id}")
            return run_id
        else:
            print("❌ 保存失败")
            return None
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return None


def example_4_query_scheduling_result(run_id: str):
    """示例4: 查询排仓结果"""
    print("\n" + "=" * 50)
    print("示例4: 查询排仓结果")
    print("=" * 50)
    
    try:
        result = get_scheduling_result(run_id)
        if result:
            print(f"✅ 查询成功!")
            print(f"\n运行信息:")
            print(f"  - Run ID: {result['run']['run_id']}")
            print(f"  - 名称: {result['run']['run_name']}")
            print(f"  - 状态: {result['run']['status']}")
            print(f"  - 总仓面数: {result['run']['total_warehouses']}")
            print(f"  - A段: {result['run']['count_a']}")
            print(f"  - B段: {result['run']['count_b']}")
            print(f"  - C段: {result['run']['count_c']}")
            
            print(f"\n仓面列表:")
            for w in result['warehouses'][:3]:  # 只显示前3个
                print(f"  - {w['warehouse_id']}: {w['segment']}段, "
                      f"高程={w['top_elevation']}m, "
                      f"开始={w['final_start_date']}")
            
            print(f"\n权重配置:")
            for weight in result['weights']:
                print(f"  - {weight['indicator_name']}: "
                      f"AHP={weight['ahp_weight']:.3f}, "
                      f"组合={weight['combined_weight']:.3f}")
            
            print(f"\n月计划:")
            for mp in result['monthly_plans']:
                print(f"  - {mp['window_name']}: "
                      f"{mp['window_start_date']} ~ {mp['window_end_date']}, "
                      f"{mp['warehouse_count']}个仓面")
        else:
            print(f"❌ 未找到运行记录: {run_id}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")


def example_5_query_by_date_range(run_id: str):
    """示例5: 按日期范围查询"""
    print("\n" + "=" * 50)
    print("示例5: 按日期范围查询")
    print("=" * 50)
    
    try:
        with AIWARESyncService() as service:
            warehouses = service.get_warehouse_schedule_by_date_range(
                run_id=run_id,
                start_date=date(2026, 4, 1),
                end_date=date(2026, 4, 10)
            )
        
        print(f"✅ 查询到 {len(warehouses)} 个仓面:")
        for w in warehouses:
            print(f"  - {w['warehouse_id']}: {w['final_start_date']} ~ {w['final_end_date']}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")


def example_6_export_to_excel(run_id: str):
    """示例6: 导出到Excel"""
    print("\n" + "=" * 50)
    print("示例6: 导出到Excel")
    print("=" * 50)
    
    try:
        with AIWARESyncService() as service:
            df = service.export_to_dataframe(run_id)
        
        if not df.empty:
            output_file = f"./output/aiware_export_{run_id}.xlsx"
            df.to_excel(output_file, index=False)
            print(f"✅ 已导出到: {output_file}")
            print(f"  记录数: {len(df)}")
            print(f"  列: {list(df.columns)}")
        else:
            print("❌ 导出失败，数据为空")
    except Exception as e:
        print(f"❌ 导出失败: {e}")


def example_7_repository_usage():
    """示例7: 直接使用仓储层"""
    print("\n" + "=" * 50)
    print("示例7: 直接使用仓储层")
    print("=" * 50)
    
    try:
        # 使用上下文管理器
        with SchedulingRunRepository() as repo:
            # 获取最新的运行记录
            runs = repo.get_latest(limit=5)
            print(f"✅ 最新的 {len(runs)} 条运行记录:")
            for run in runs:
                print(f"  - {run.run_id}: {run.run_name} ({run.status.value})")
        
        # 查询仓面
        if runs:
            latest_run_id = runs[0].run_id
            with WarehouseScheduleRepository() as ws_repo:
                # 获取A段仓面
                a_warehouses = ws_repo.get_by_segment(latest_run_id, Segment.A)
                print(f"\nA段仓面 ({len(a_warehouses)}个):")
                for w in a_warehouses[:3]:
                    print(f"  - {w.warehouse_id}: {w.final_start_date} ~ {w.final_end_date}")
                
                # 按日期范围查询
                b_warehouses = ws_repo.get_by_segment(latest_run_id, Segment.B)
                print(f"\nB段仓面 ({len(b_warehouses)}个):")
                for w in b_warehouses[:3]:
                    print(f"  - {w.warehouse_id}: 得分={w.score:.3f}, 排名={w.priority_rank}")
    
    except Exception as e:
        print(f"❌ 查询失败: {e}")


def main():
    """主函数 - 运行所有示例"""
    print("AIWARE 数据库模块使用示例")
    print("=" * 50)
    
    # 1. 测试连接
    if not example_1_test_connection():
        print("\n请先确保数据库服务已启动!")
        return
    
    # 2. 初始化数据库
    example_2_init_database()
    
    # 3. 保存排仓结果
    run_id = example_3_save_scheduling_result()
    
    if run_id:
        # 4. 查询排仓结果
        example_4_query_scheduling_result(run_id)
        
        # 5. 按日期范围查询
        example_5_query_by_date_range(run_id)
        
        # 6. 导出到Excel
        example_6_export_to_excel(run_id)
    
    # 7. 使用仓储层
    example_7_repository_usage()
    
    print("\n" + "=" * 50)
    print("所有示例执行完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
