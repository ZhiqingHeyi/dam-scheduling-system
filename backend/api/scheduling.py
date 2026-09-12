from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
import json
import os
from config import settings
from core.scheduling_algorithm import (
    load_ahp_weights, compute_entropy_weights, compute_combined_weights,
    normalize_for_scoring, sort_warehouses_by_score, correct_layer_order,
    elevation_constraint_sort, extract_dam_ids, extract_layer_ids,
    CraneScheduler, WinterScheduleHandler, SchedulingConfig,
    ScheduleCompressionConfig, ScheduleCompressor,
    build_complete_schedule, build_owner_export_table,
    export_plan_windows, get_fixed_monthly_window, get_next_fixed_monthly_window, get_rolling_window,
    filter_table_by_overlap, reschedule_c_with_winter,
    build_cross_tab_data, build_cross_tab_export,
    _get_dam_elev_file_lookup
)
from api.database import sync_data_from_database

router = APIRouter()


class SchedulingRequest(BaseModel):
    start_date: str = None
    deadline_date: str = None
    use_compression: bool = False
    alpha: float = 0.5
    water_storage_date: str = None
    water_storage_elevation: float = 920.0
    completion_date: str = None
    compress_interval: bool = True
    interval_min: int = 14
    interval_max: int = 20
    interval_reduction: int = 1
    critical_path_first: bool = True


class SchedulingResponse(BaseModel):
    success: bool
    message: str
    final_mode: str = ""
    final_end_date: str = ""
    used_compression: bool = False
    visualization_data: dict = {}
    debug_info: dict = {}
    schedule_data: list = []
    sorted_report: list = []

    class Config:
        extra = "allow"


async def run_scheduling_pipeline(request: SchedulingRequest, progress_callback=None):
    try:
        if progress_callback:
            await progress_callback(1, 10, "正在准备数据...", "检查数据文件并同步数据库")

        base_file = os.path.join(settings.UPLOAD_DIR, 'BaselineSchedule.xlsx')
        actual_file = os.path.join(settings.UPLOAD_DIR, 'ActualDone.xlsx')
        warehouse_file = os.path.join(settings.UPLOAD_DIR, 'WarehouseData_filled.xlsx')
        ahp_file = os.path.join(settings.UPLOAD_DIR, 'AHPScores.xlsx')

        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        if not os.path.exists(base_file):
            if progress_callback:
                await progress_callback(1, 10, "正在同步数据...", "从数据库导出基准计划等数据")

            try:
                async def sync_progress(step, total, status, detail):
                    if progress_callback:
                        await progress_callback(step, total, status, detail)

                sync_result = await sync_data_from_database(sync_progress)

                if isinstance(sync_result, dict) and not sync_result.get('success'):
                    raise Exception(f"数据同步失败: {sync_result.get('message', '未知错误')}")

            except HTTPException as sync_http_error:
                raise FileNotFoundError(
                    f"未找到基准计划文件且数据同步失败: {sync_http_error.detail}。请先点击'数据库同步'按钮。")
            except FileNotFoundError:
                raise
            except Exception as sync_error:
                raise FileNotFoundError(
                    f"未找到基准计划文件且数据同步失败: {str(sync_error)}。请先点击'数据库同步'按钮。")

        if progress_callback:
            await progress_callback(2, 10, "正在加载数据...", "读取基准计划和实际完成数据")

        base_df = pd.read_excel(base_file)
        for col in ['PlanStart', 'PlanEnd']:
            if col in base_df.columns:
                base_df[col] = pd.to_datetime(base_df[col])
        if 'TopElev' in base_df.columns:
            base_df['TopElev'] = pd.to_numeric(base_df['TopElev'], errors='coerce')

        dam_elev_file = os.path.join(settings.UPLOAD_DIR, 'DamElevation.xlsx')
        if os.path.exists(dam_elev_file) and 'TopElev' in base_df.columns:
            missing_before = base_df['TopElev'].isna().sum()
            if missing_before > 0:
                try:
                    dam_elev_df = pd.read_excel(dam_elev_file)
                    dam_elev_df['TopElev'] = pd.to_numeric(dam_elev_df['TopElev'], errors='coerce')
                    elev_map = {}
                    for _, er in dam_elev_df.iterrows():
                        d = int(er['DamID']) if not pd.isna(er.get('DamID')) else None
                        l = int(er['LayerID']) if not pd.isna(er.get('LayerID')) else None
                        e = float(er['TopElev']) if not pd.isna(er.get('TopElev')) else None
                        if d is not None and l is not None and e is not None:
                            elev_map[(d, l)] = e
                    filled = 0
                    for idx, row in base_df.iterrows():
                        if pd.isna(row.get('TopElev')):
                            key = (int(row['DamID']), int(row['LayerID']))
                            if key in elev_map:
                                base_df.at[idx, 'TopElev'] = elev_map[key]
                                filled += 1
                    if progress_callback and filled > 0:
                        await progress_callback(2, 10, "INFO", f"从DamElevation.xlsx补全 {filled} 条高程数据")
                except Exception:
                    pass

        act_df = pd.DataFrame()
        if os.path.exists(actual_file):
            act_df = pd.read_excel(actual_file)
            for col in ['ActualStart', 'ActualEnd']:
                if col in act_df.columns:
                    act_df[col] = pd.to_datetime(act_df[col])

        if progress_callback:
            await progress_callback(3, 10, "正在进行ABC分段划分...", "根据实际完成进度划分A/B/C段")

        a_idx, b_idx, c_idx, t_cut_plan, b1_idx, b2_idx = split_schedule_abc(
            base_df, act_df, settings.N_EXTRA
        )

        if len(b_idx) == 0:
            raise Exception("B段仓面为空，无法进行排仓计算。请检查实际完成数据是否与基准计划匹配。")

        if progress_callback:
            await progress_callback(4, 10, "正在生成B段仓面数据...",
                                    f"提取B段仓面指标数据（{len(b_idx)}个仓面）")

        b_data = make_warehouse_data_b(base_df, b_idx, warehouse_file)

        wh_file = os.path.join(settings.UPLOAD_DIR, 'WarehouseData.xlsx')
        b_data.to_excel(wh_file, index=False, sheet_name='B段仓面数据')

        if progress_callback:
            await progress_callback(5, 10, "正在计算权重（AHP + 熵权法）...", "组合赋权计算")

        if os.path.exists(ahp_file):
            ahp_weights, cr = load_ahp_weights(ahp_file)
        else:
            ahp_weights = np.array([0.25, 0.20, 0.18, 0.15, 0.12, 0.10])
            cr = 0.05

        score_indicators = b_data.iloc[:, 1:7].values.astype(float)
        entropy_weights = compute_entropy_weights(score_indicators)

        config = SchedulingConfig(alpha=request.alpha)
        combined_weights = compute_combined_weights(ahp_weights, entropy_weights, config.alpha)

        is_benefit = np.ones(score_indicators.shape[1], dtype=bool)
        if score_indicators.shape[1] >= 5:
            is_benefit[4] = False

        x_score = normalize_for_scoring(score_indicators, is_benefit)

        if progress_callback:
            await progress_callback(6, 10, "正在执行排序算法...", "得分排序→层号纠正→高差约束微调")

        warehouse_ids = b_data.iloc[:, 0].astype(str).tolist()
        dam_ids = extract_dam_ids(warehouse_ids)
        layer_ids = extract_layer_ids(warehouse_ids)

        sorted_indices, scores = sort_warehouses_by_score(warehouse_ids, x_score, combined_weights)

        sorted_indices, sorted_dam, sorted_layer = correct_layer_order(
            sorted_indices, dam_ids, layer_ids, warehouse_ids, scores
        )

        dam_list_a, heights_a = extract_a_segment_heights(base_df, act_df, a_idx)

        final_order = elevation_constraint_sort(
            sorted_indices, dam_ids, layer_ids, score_indicators,
            config.base_elev_const, config.adj_height_limit, config.global_height_limit,
            dam_list_a, heights_a
        )

        total_cols = len(b_data.columns)
        if total_cols >= 4:
            crane_col_name = b_data.columns[-2]
            rest_col_name = b_data.columns[-1]
            crane_data = b_data.iloc[final_order, -2].values
            rest_data = b_data.iloc[final_order, -1].values
        else:
            crane_col_name = '缆机数量'
            rest_col_name = '间歇时间'
            crane_data = np.ones(len(final_order))
            rest_data = np.full(len(final_order), 10.0)

        sorted_report = pd.DataFrame({
            'WarehouseID': [warehouse_ids[i] for i in final_order],
            'Score': scores[final_order],
            crane_col_name: crane_data,
            rest_col_name: rest_data
        })

        if progress_callback:
            await progress_callback(7, 10, "正在进行缆机排班...", "按缆机数量和间歇时间排班")

        start_dt = datetime.strptime(request.start_date, '%Y/%m/%d') if request.start_date else datetime.now()

        scheduler = CraneScheduler(config)

        if request.use_compression:
            if progress_callback:
                await progress_callback(8, 10, "正在执行压缩工期排班...", "压缩模式：缩短间歇时间+关键路径优先")
            schedule_normal = scheduler.schedule_by_crane_and_gap(sorted_report, start_dt, 'compress')

            winter_handler = WinterScheduleHandler(config)
            schedule_with_winter = winter_handler.apply_winter_to_schedule(schedule_normal)

            compression_config = ScheduleCompressionConfig(
                use_compression=True,
                water_storage_date=request.water_storage_date or '2028/10/01',
                water_storage_elevation=request.water_storage_elevation,
                completion_date=request.completion_date or '2030/10/15',
                compress_interval=request.compress_interval,
                interval_min=request.interval_min,
                interval_max=request.interval_max,
                interval_reduction=request.interval_reduction,
                critical_path_first=request.critical_path_first
            )

            compressor = ScheduleCompressor(compression_config, config)
            schedule_compressed, compression_log = compressor.compress_schedule(
                schedule_with_winter, base_df, b_idx, sorted_report, start_dt
            )
            schedule_with_winter = schedule_compressed
        else:
            if progress_callback:
                await progress_callback(8, 10, "正在处理冬歇期...", "调整冬歇期排仓计划")

            schedule_normal = scheduler.schedule_by_crane_and_gap(sorted_report, start_dt, 'normal')

            winter_handler = WinterScheduleHandler(config)
            schedule_with_winter = winter_handler.apply_winter_to_schedule(schedule_normal)

        t_all, t_a_out, t_c_out = build_complete_schedule(
            schedule_with_winter, a_idx, b_idx, c_idx, base_df, act_df, config
        )

        if progress_callback:
            await progress_callback(9, 10, "正在校验工期约束...", "检查蓄水发电和完工日期约束")

        final_mode = "正常模式"
        used_compression = False
        is_deadline_satisfied = True
        overdue_days = 0
        compression_result_info = {}

        if request.use_compression:
            used_compression = True
            final_mode = "压缩工期模式"

            compressor_check = ScheduleCompressor(
                ScheduleCompressionConfig(
                    use_compression=True,
                    water_storage_date=request.water_storage_date or '2028/10/01',
                    water_storage_elevation=request.water_storage_elevation,
                    completion_date=request.completion_date or '2030/10/15'
                ), config
            )
            constraint_check = compressor_check.check_constraints(t_all)
            compression_result_info = constraint_check

            if constraint_check['water_storage_satisfied'] and constraint_check['completion_satisfied']:
                final_mode = "压缩工期模式-满足全部约束"
            elif constraint_check['water_storage_satisfied']:
                final_mode = "压缩工期模式-满足蓄水约束"
            elif constraint_check['completion_satisfied']:
                final_mode = "压缩工期模式-满足完工约束"
            else:
                final_mode = "压缩工期模式-约束未满足"

            compression_result_info.update(compression_log)
        else:
            use_deadline = request.deadline_date is not None and request.deadline_date.strip() != ''
            if use_deadline:
                deadline_dt = datetime.strptime(request.deadline_date, '%Y/%m/%d')
                deadline_ts = pd.Timestamp(deadline_dt)
                final_end_ts = pd.to_datetime(t_all['FinalEnd']).max()

                if final_end_ts > deadline_ts:
                    final_mode = "正常模式超期"
                    is_deadline_satisfied = False
                    overdue_days = (final_end_ts - deadline_ts).days
                else:
                    final_mode = "正常模式满足工期"
                    is_deadline_satisfied = True

        if progress_callback:
            await progress_callback(10, 10, "正在生成输出文件...", "导出排仓计划和可视化数据")

        run_result = save_output_files(t_all, request)
        run_folder = run_result['run_id']
        plan_files_info = run_result.get('plan_files', {})

        visualization_data = build_visualization_data(t_all, schedule_with_winter, sorted_report, final_mode)

        consistency_viz = visualization_data.get('consistencyCheck', {})
        consistency_export = {
            'fixedCount': plan_files_info.get('fixed_count', -1),
            'rollingCount': plan_files_info.get('rolling_count', -1),
        }
        consistency_ok = (
            consistency_viz.get('fixedCount') == consistency_export['fixedCount']
            and consistency_viz.get('rollingCount') == consistency_export['rollingCount']
        )

        t_export = build_owner_export_table(t_all)

        schedule_records = []
        for _, row in schedule_with_winter.iterrows():
            rec = {}
            for k, v in row.items():
                rec[k] = _safe_convert(v)
            schedule_records.append(rec)

        sorted_records = []
        for _, row in sorted_report.iterrows():
            rec = {}
            for k, v in row.items():
                rec[k] = _safe_convert(v)
            sorted_records.append(rec)

        export_records = []
        for _, row in t_export.iterrows():
            rec = {}
            for k, v in row.items():
                rec[k] = _safe_convert(v)
            export_records.append(rec)

        debug_info = {
            'ahp_weights': ahp_weights.tolist(),
            'entropy_weights': entropy_weights.tolist(),
            'combined_weights': combined_weights.tolist(),
            'cr': float(cr),
            'n_warehouses': len(final_order),
            'n_a': len(a_idx),
            'n_b': len(b_idx),
            'n_c': len(c_idx),
            'final_mode': final_mode,
            'is_deadline_satisfied': is_deadline_satisfied,
            'overdue_days': overdue_days,
            'used_compression': used_compression
        }

        if used_compression:
            debug_info['water_storage_satisfied'] = compression_result_info.get('water_storage_satisfied', False)
            debug_info['completion_satisfied'] = compression_result_info.get('completion_satisfied', False)
            debug_info['original_end_date'] = compression_result_info.get('original_end_date', '')
            debug_info['saved_days'] = compression_result_info.get('saved_days', 0)
            debug_info['interval_compressed'] = compression_result_info.get('interval_compressed', 0)
            debug_info['critical_path_adjusted'] = compression_result_info.get('critical_path_adjusted', False)

        return {
            'success': True,
            'message': '排仓计算完成',
            'final_mode': final_mode,
            'final_end_date': str(pd.to_datetime(t_all['FinalEnd']).max()) if len(t_all) > 0 else '',
            'used_compression': used_compression,
            'visualization_data': visualization_data,
            'debug_info': debug_info,
            'schedule_data': schedule_records,
            'sorted_report': sorted_records,
            'export_data': export_records,
            'run_folder': run_folder,
            'consistency_check': {
                'ok': consistency_ok,
                'viz_fixed_count': consistency_viz.get('fixedCount'),
                'export_fixed_count': consistency_export['fixedCount'],
                'viz_rolling_count': consistency_viz.get('rollingCount'),
                'export_rolling_count': consistency_export['rollingCount'],
                'fixed_window_range': consistency_viz.get('fixedWindowRange'),
                'rolling_window_range': consistency_viz.get('rollingWindowRange'),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error in save_output_files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _safe_convert(v):
    if isinstance(v, (pd.Timestamp, datetime)):
        return str(v)
    elif hasattr(v, 'isoformat'):
        return v.isoformat()
    elif isinstance(v, (np.integer,)):
        return int(v)
    elif isinstance(v, (np.floating,)):
        return float(v)
    elif isinstance(v, float) and pd.isna(v):
        return None
    elif isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def extract_a_segment_heights(base_df: pd.DataFrame, act_df: pd.DataFrame,
                              a_idx: List[int]) -> Tuple[List[int], List[float]]:
    dam_list_a = []
    heights_a = []

    if len(act_df) == 0 or 'DamID' not in act_df.columns or 'LayerID' not in act_df.columns:
        return dam_list_a, heights_a

    act_dam = act_df['DamID'].values
    act_layer = act_df['LayerID'].values

    if 'ActualTopElev' in act_df.columns:
        dam_max_actual_elev = {}
        for _, row in act_df.iterrows():
            d = row.get('DamID')
            elev = row.get('ActualTopElev')
            if pd.isna(d) or pd.isna(elev):
                continue
            d_int = int(d)
            if d_int not in dam_max_actual_elev or float(elev) > dam_max_actual_elev[d_int]:
                dam_max_actual_elev[d_int] = float(elev)

        if dam_max_actual_elev:
            for d_int, max_elev in dam_max_actual_elev.items():
                dam_list_a.append(d_int)
                heights_a.append(max_elev)
            return dam_list_a, heights_a

    u_dam_a = {}
    for d, l in zip(act_dam, act_layer):
        if pd.isna(d) or pd.isna(l):
            continue
        d_int = int(d)
        if d_int not in u_dam_a or l > u_dam_a[d_int]:
            u_dam_a[d_int] = int(l)

    if 'TopElev' not in base_df.columns:
        return dam_list_a, heights_a

    base_dam = base_df['DamID'].values
    base_layer = base_df['LayerID'].values
    top_elev = base_df['TopElev'].values

    for d_int, last_layer in u_dam_a.items():
        mask = (base_dam == d_int) & (base_layer == last_layer)
        if mask.any():
            idx = np.where(mask)[0][0]
            h = top_elev[idx]
            if not pd.isna(h):
                dam_list_a.append(d_int)
                heights_a.append(float(h))

    return dam_list_a, heights_a


def save_output_files(t_all: pd.DataFrame, request: SchedulingRequest) -> dict:
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    run_id = datetime.now().strftime("Run_%Y%m%d_%H%M%S")
    run_dir = os.path.join(settings.OUTPUT_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    plan_files_info = {}
    try:
        t_export = build_owner_export_table(t_all)
        export_file = os.path.join(run_dir, '完整排仓计划.xlsx')
        t_export.to_excel(export_file, index=False, sheet_name='完整排仓计划')

        plan_files_info = export_plan_windows(t_all, run_dir)

        cross_tab_file = os.path.join(run_dir, '大坝仓位总排仓计划表.xlsx')
        build_cross_tab_export(t_all, cross_tab_file)

    except Exception as e:
        import logging
        logging.error(f"Error in save_output_files: {e}", exc_info=True)

    return {'run_id': run_id, 'plan_files': plan_files_info}


def split_schedule_abc(base_df: pd.DataFrame, act_df: pd.DataFrame, n_extra: int = 10):
    n_base = len(base_df)

    matched_indices = []
    plan_finish_done = []

    if len(act_df) > 0 and 'DamID' in act_df.columns and 'LayerID' in act_df.columns:
        for _, row in act_df.iterrows():
            d, l = row.get('DamID'), row.get('LayerID')
            if pd.isna(d) or pd.isna(l):
                continue

            mask = (base_df['DamID'] == d) & (base_df['LayerID'] == l)
            idx = base_df[mask].index

            if len(idx) > 0:
                matched_indices.append(idx[0])
                if 'PlanEnd' in base_df.columns:
                    plan_finish_done.append(base_df.loc[idx[0], 'PlanEnd'])

    valid_mask = [i for i in range(len(matched_indices))
                  if i < len(plan_finish_done) and not pd.isna(plan_finish_done[i])]

    if valid_mask:
        t_cut_plan = max([plan_finish_done[i] for i in valid_mask])
    else:
        t_cut_plan = base_df['PlanEnd'].min() if 'PlanEnd' in base_df.columns else pd.Timestamp.now()

    a_idx = list(set([matched_indices[i] for i in valid_mask]))

    if len(act_df) > 0 and 'ActualTopElev' in act_df.columns and 'TopElev' in base_df.columns:
        dam_max_actual_elev = {}
        dam_last_actual_record = {}
        for _, row in act_df.iterrows():
            d = row.get('DamID')
            elev = row.get('ActualTopElev')
            if pd.isna(d) or pd.isna(elev):
                continue
            d_int = int(d)
            if d_int not in dam_max_actual_elev or float(elev) > dam_max_actual_elev[d_int]:
                dam_max_actual_elev[d_int] = float(elev)
                dam_last_actual_record[d_int] = row

        elev_covered_indices = []
        for i in range(n_base):
            if i in a_idx:
                continue
            d = base_df.iloc[i].get('DamID')
            top_elev = base_df.iloc[i].get('TopElev')
            if pd.isna(d) or pd.isna(top_elev):
                continue
            d_int = int(d)
            if d_int in dam_max_actual_elev and float(top_elev) <= dam_max_actual_elev[d_int]:
                elev_covered_indices.append(i)

        if elev_covered_indices:
            a_idx.extend(elev_covered_indices)
            a_idx = list(set(a_idx))

            for i in elev_covered_indices:
                d = base_df.iloc[i].get('DamID')
                l = base_df.iloc[i].get('LayerID')
                if pd.isna(d) or pd.isna(l):
                    continue
                d_int = int(d)
                if d_int in dam_last_actual_record:
                    ref_row = dam_last_actual_record[d_int]
                    new_row = {
                        'DamID': int(d),
                        'LayerID': int(l),
                        'ActualStart': ref_row.get('ActualStart'),
                        'ActualEnd': ref_row.get('ActualEnd')
                    }
                    if 'ActualTopElev' in ref_row and not pd.isna(ref_row.get('ActualTopElev')):
                        new_row['ActualTopElev'] = float(ref_row['ActualTopElev'])
                    act_df = pd.concat([act_df, pd.DataFrame([new_row])], ignore_index=True)

    all_idx = list(range(n_base))

    if 'PlanEnd' in base_df.columns:
        before_mask = base_df['PlanEnd'] <= t_cut_plan
        after_mask = base_df['PlanEnd'] > t_cut_plan
    else:
        before_mask = pd.Series([False] * n_base)
        after_mask = pd.Series([True] * n_base)

    is_a = [i in a_idx for i in all_idx]

    b1_idx = [i for i in range(n_base) if before_mask.iloc[i] and not is_a[i]]

    after_indices = [i for i in range(n_base) if after_mask.iloc[i] and not is_a[i]]
    after_sorted = sorted(after_indices,
                          key=lambda x: base_df.loc[x, 'PlanEnd'] if 'PlanEnd' in base_df.columns else 0)
    n_pick = min(n_extra, len(after_sorted))
    b2_idx = after_sorted[:n_pick]

    b_idx = list(set(b1_idx + b2_idx))
    c_idx = [i for i in all_idx if i not in a_idx and i not in b_idx]

    return a_idx, b_idx, c_idx, t_cut_plan, b1_idx, b2_idx


def make_warehouse_data_b(base_df: pd.DataFrame, b_idx: List[int],
                          data_file: str = './uploads/WarehouseData_filled.xlsx') -> pd.DataFrame:
    dam_b = base_df.iloc[b_idx]['DamID'].values
    layer_b = base_df.iloc[b_idx]['LayerID'].values

    id_b = [f"{int(d)}-{int(l)}" for d, l in zip(dam_b, layer_b)]

    if os.path.exists(data_file):
        df_w = pd.read_excel(data_file)
        wid_all = df_w.iloc[:, 0].astype(str).tolist()

        tf = [id in wid_all for id in id_b]
        loc = [wid_all.index(id) if id in wid_all else -1 for id in id_b]

        valid_loc = [loc[i] for i in range(len(loc)) if tf[i]]
        return df_w.iloc[valid_loc].reset_index(drop=True)
    else:
        return pd.DataFrame({
            '仓面编号': id_b,
            '坝段高程（到坝顶距离/m）': np.random.rand(len(id_b)) * 100,
            '奇偶坝段': np.random.randint(0, 2, len(id_b)),
            '孔口坝段': np.random.randint(0, 2, len(id_b)),
            '浇筑方量（m³）': np.random.rand(len(id_b)) * 5000,
            '顶块间歇时间（h）': np.random.rand(len(id_b)) * 100,
            '浇筑强度（m³/h）': np.random.rand(len(id_b)) * 300,
            '缆机数量': np.ones(len(id_b)),
            '间歇时间（天）': np.full(len(id_b), 10.0)
        })


def build_visualization_data(t_all: pd.DataFrame, schedule_df: pd.DataFrame,
                            sorted_report: pd.DataFrame,
                            final_mode: str = '正常模式') -> dict:
    if t_all is None or len(t_all) == 0:
        return {'available': False}

    schedule_start = pd.Timestamp(t_all['FinalStart'].min())
    schedule_end = pd.Timestamp(t_all['FinalEnd'].max())

    all_poured = t_all[t_all['Segment'] == 'A'].copy() if 'Segment' in t_all.columns else t_all.iloc[0:0].copy()

    full_elev_lookup = _build_elev_lookup(t_all)

    now = pd.Timestamp.now()
    fixed_window = get_fixed_monthly_window(now)
    next_window = get_next_fixed_monthly_window(now)
    rolling_start, rolling_end = get_rolling_window(t_all)

    fixed_data = filter_table_by_overlap(t_all, fixed_window[0], fixed_window[1])
    next_data = filter_table_by_overlap(t_all, next_window[0], next_window[1])
    rolling_data = filter_table_by_overlap(t_all, rolling_start, rolling_end)

    fixed_chart = prepare_chart_data_with_poured(fixed_data, all_poured, full_elev_lookup)
    next_chart = prepare_chart_data_with_poured(next_data, all_poured, full_elev_lookup)
    rolling_chart = prepare_chart_data_with_poured(rolling_data, all_poured, full_elev_lookup)

    fixed_chart['windowStart'] = str(fixed_window[0])
    fixed_chart['windowEnd'] = str(fixed_window[1])
    fixed_chart['totalCount'] = len(fixed_data)
    fixed_chart['segmentCounts'] = _count_by_segment(fixed_data)

    next_chart['windowStart'] = str(next_window[0])
    next_chart['windowEnd'] = str(next_window[1])
    next_chart['totalCount'] = len(next_data)
    next_chart['segmentCounts'] = _count_by_segment(next_data)

    rolling_chart['windowStart'] = str(rolling_start)
    rolling_chart['windowEnd'] = str(rolling_end)
    rolling_chart['totalCount'] = len(rolling_data)
    rolling_chart['segmentCounts'] = _count_by_segment(rolling_data)

    return {
        'available': True,
        'finalMode': final_mode,
        'scheduleStart': str(schedule_start),
        'scheduleEnd': str(schedule_end),
        'fixedWindow': fixed_chart,
        'nextMonthWindow': next_chart,
        'rollingWindow': rolling_chart,
        'consistencyCheck': {
            'fixedWindowRange': f"{fixed_window[0].strftime('%Y%m%d')}-{fixed_window[1].strftime('%Y%m%d')}",
            'nextMonthWindowRange': f"{next_window[0].strftime('%Y%m%d')}-{next_window[1].strftime('%Y%m%d')}",
            'rollingWindowRange': f"{rolling_start.strftime('%Y%m%d')}-{rolling_end.strftime('%Y%m%d')}",
            'fixedCount': len(fixed_data),
            'nextMonthCount': len(next_data),
            'rollingCount': len(rolling_data),
            'totalWarehouses': len(t_all),
            'referenceDate': str(now.normalize())
        }
    }


def _count_by_segment(df: pd.DataFrame) -> dict:
    if df is None or len(df) == 0:
        return {'A': 0, 'B': 0, 'C': 0}
    seg = df['Segment'].value_counts().to_dict()
    return {
        'A': int(seg.get('A', 0)),
        'B': int(seg.get('B', 0)),
        'C': int(seg.get('C', 0))
    }


def _build_elev_lookup(df: pd.DataFrame) -> dict:
    # 先用 DamElevation.xlsx 的完整高程数据作为基础
    lookup = dict(_get_dam_elev_file_lookup())
    if df is None or len(df) == 0 or 'TopElev' not in df.columns:
        return lookup
    # 再用传入的df中的真实TopElev覆盖
    for _, row in df.iterrows():
        dam_id = int(row['DamID']) if not pd.isna(row.get('DamID')) else None
        layer_id = int(row['LayerID']) if not pd.isna(row.get('LayerID')) else None
        elev = row.get('TopElev')
        if dam_id is not None and layer_id is not None and not pd.isna(elev):
            lookup[(dam_id, layer_id)] = float(elev)
    return lookup


DAM_CREST_ELEV = 990.0  # 大坝坝顶高程


def _resolve_top_elev(dam_id: int, layer_id: int, elev_lookup: dict) -> float:
    key = (dam_id, layer_id)
    if key in elev_lookup:
        return min(elev_lookup[key], DAM_CREST_ELEV)
    dam_elevs = {lid: elev for (did, lid), elev in elev_lookup.items() if did == dam_id}
    if dam_elevs:
        sorted_layers = sorted(dam_elevs.keys())
        if layer_id <= sorted_layers[0]:
            return min(dam_elevs[sorted_layers[0]] - (sorted_layers[0] - layer_id) * 3.0, DAM_CREST_ELEV)
        elif layer_id >= sorted_layers[-1]:
            return min(dam_elevs[sorted_layers[-1]] + (layer_id - sorted_layers[-1]) * 3.0, DAM_CREST_ELEV)
        else:
            lower = max(l for l in sorted_layers if l < layer_id)
            upper = min(l for l in sorted_layers if l > layer_id)
            t = (layer_id - lower) / (upper - lower)
            return min(dam_elevs[lower] + t * (dam_elevs[upper] - dam_elevs[lower]), DAM_CREST_ELEV)
    return min(round(layer_id * 3, 2), DAM_CREST_ELEV)


LAYER_HEIGHT = 3.0


def _compute_bottom_elev(dam_id: int, layer_id: int, top_elev: float,
                         elev_lookup: dict) -> float:
    prev_layer = layer_id - 1
    prev_key = (dam_id, prev_layer)
    if prev_key in elev_lookup:
        return float(elev_lookup[prev_key])
    dam_elevs = {lid: elev for (did, lid), elev in elev_lookup.items() if did == dam_id and lid < layer_id}
    if dam_elevs:
        max_lower_layer = max(dam_elevs.keys())
        return float(dam_elevs[max_lower_layer])
    return top_elev - LAYER_HEIGHT


def prepare_chart_data(df: pd.DataFrame, full_elev_lookup: dict = None) -> dict:
    if df is None or len(df) == 0:
        return {'dams': [], 'warehouses': []}

    df = df.copy()
    df['FinalStart'] = pd.to_datetime(df['FinalStart'])
    df = df.sort_values('FinalStart')

    dams = sorted(df['DamID'].dropna().astype(int).unique().tolist())
    elev_lookup = full_elev_lookup if full_elev_lookup else _build_elev_lookup(df)

    warehouses = []
    for idx, row in df.iterrows():
        dam_id = int(row['DamID']) if not pd.isna(row['DamID']) else 0
        layer_id = int(row['LayerID']) if not pd.isna(row['LayerID']) else 0
        top_elev = _resolve_top_elev(dam_id, layer_id, elev_lookup)
        bottom_elev = _compute_bottom_elev(dam_id, layer_id, top_elev, elev_lookup)
        warehouses.append({
            'damId': dam_id,
            'layerId': layer_id,
            'warehouseId': str(row['WarehouseID']),
            'startTime': str(row['FinalStart']),
            'endTime': str(row['FinalEnd']),
            'segment': str(row['Segment']),
            'topElev': round(top_elev, 2),
            'bottomElev': round(bottom_elev, 2),
            'elevation': round((top_elev + bottom_elev) / 2, 2),
            'displayOrder': len(warehouses) + 1
        })

    return {'dams': dams, 'warehouses': warehouses}


def prepare_chart_data_with_poured(window_df: pd.DataFrame, all_poured: pd.DataFrame,
                                   full_elev_lookup: dict = None) -> dict:
    if (window_df is None or len(window_df) == 0) and (all_poured is None or len(all_poured) == 0):
        return {'dams': [], 'warehouses': []}

    if window_df is None or len(window_df) == 0:
        return prepare_chart_data(all_poured, full_elev_lookup)

    window_df = window_df.copy()
    window_df['FinalStart'] = pd.to_datetime(window_df['FinalStart'], errors='coerce')

    if full_elev_lookup:
        elev_lookup = full_elev_lookup
    else:
        combined = pd.concat([window_df, all_poured], ignore_index=True) if all_poured is not None and len(all_poured) > 0 else window_df
        elev_lookup = _build_elev_lookup(combined)

    planned_dams = set(window_df['DamID'].dropna().astype(int).unique().tolist())

    if all_poured is not None and len(all_poured) > 0:
        poured_dams = set(all_poured['DamID'].dropna().astype(int).unique().tolist())
    else:
        poured_dams = set()

    all_dams = sorted(planned_dams | poured_dams)

    window_warehouses = []
    for idx, row in window_df.iterrows():
        dam_id = int(row['DamID']) if not pd.isna(row['DamID']) else 0
        layer_id = int(row['LayerID']) if not pd.isna(row['LayerID']) else 0
        top_elev = _resolve_top_elev(dam_id, layer_id, elev_lookup)
        bottom_elev = _compute_bottom_elev(dam_id, layer_id, top_elev, elev_lookup)
        window_warehouses.append({
            'damId': dam_id,
            'layerId': layer_id,
            'warehouseId': str(row['WarehouseID']),
            'startTime': '' if pd.isna(row['FinalStart']) else str(row['FinalStart']),
            'endTime': '' if pd.isna(row['FinalEnd']) else str(row['FinalEnd']),
            'segment': str(row['Segment']),
            'topElev': round(top_elev, 2),
            'bottomElev': round(bottom_elev, 2),
            'elevation': round((top_elev + bottom_elev) / 2, 2),
            'displayOrder': len(window_warehouses) + 1
        })

    window_wh_ids = set(wh['warehouseId'] for wh in window_warehouses)

    poured_warehouses = []
    if all_poured is not None and len(all_poured) > 0:
        for idx, row in all_poured.iterrows():
            dam_id = int(row['DamID']) if not pd.isna(row['DamID']) else 0
            layer_id = int(row['LayerID']) if not pd.isna(row['LayerID']) else 0
            wh_id = str(row['WarehouseID'])
            if wh_id in window_wh_ids:
                continue
            if dam_id not in all_dams:
                continue
            top_elev = _resolve_top_elev(dam_id, layer_id, elev_lookup)
            bottom_elev = _compute_bottom_elev(dam_id, layer_id, top_elev, elev_lookup)
            poured_warehouses.append({
                'damId': dam_id,
                'layerId': layer_id,
                'warehouseId': wh_id,
                'startTime': '' if pd.isna(row.get('FinalStart', '')) else str(row.get('FinalStart', '')),
                'endTime': '' if pd.isna(row.get('FinalEnd', '')) else str(row.get('FinalEnd', '')),
                'segment': 'A',
                'topElev': round(top_elev, 2),
                'bottomElev': round(bottom_elev, 2),
                'elevation': round((top_elev + bottom_elev) / 2, 2),
                'displayOrder': 0
            })

    return {'dams': all_dams, 'warehouses': window_warehouses + poured_warehouses}


@router.post("/run", response_model=SchedulingResponse)
async def run_scheduling(request: SchedulingRequest, background_tasks: BackgroundTasks):
    from main import app

    async def progress_callback(step, total, status, detail):
        if hasattr(app.state, 'connection_manager'):
            await app.state.connection_manager.broadcast_progress(step, total, status, detail)

    result = await run_scheduling_pipeline(request, progress_callback)

    if hasattr(app.state, 'connection_manager'):
        await app.state.connection_manager.broadcast_result(result)

    return SchedulingResponse(**result)


@router.get("/status")
async def get_scheduling_status():
    return {
        "status": "ready",
        "message": "排仓系统就绪",
        "config": {
            "alpha": settings.SCHEDULING_ALPHA,
            "maxCranePerDay": settings.MAX_CRANE_PER_DAY,
            "minGapDays": settings.MIN_GAP_DAYS,
        }
    }
