import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SchedulingConfig:
    alpha: float = 0.5
    max_crane_per_day: int = 4
    min_gap_days: int = 7
    max_gap_days: int = 20
    max_diff_days: int = 5
    n_extra: int = 10
    winter_start_month: int = 11
    winter_start_day: int = 1
    winter_end_month: int = 4
    winter_end_day: int = 10
    base_elev_const: float = 990.0
    adj_height_limit: float = 6.0
    global_height_limit: float = 12.0


def load_ahp_weights(ahp_file: str) -> Tuple[np.ndarray, float]:
    xls = pd.ExcelFile(ahp_file)
    sheet_names = xls.sheet_names
    num_experts = len(sheet_names)

    temp_matrix = pd.read_excel(xls, sheet_names[0], header=None).values
    n = temp_matrix.shape[0]
    if temp_matrix.shape[0] != temp_matrix.shape[1]:
        raise ValueError(f'AHP判断矩阵必须是方阵！工作表：{sheet_names[0]}')

    all_matrices = np.zeros((n, n, num_experts))
    for k, sname in enumerate(sheet_names):
        mk = pd.read_excel(xls, sname, header=None).values
        if mk.shape[0] != n or mk.shape[1] != n:
            raise ValueError(f'工作表 {sname} 的判断矩阵维度不一致')
        all_matrices[:, :, k] = mk

    composite_matrix = np.ones((n, n))
    for i in range(n):
        for j in range(n):
            composite_matrix[i, j] = np.prod(all_matrices[i, j, :]) ** (1.0 / num_experts)

    col_sum = composite_matrix.sum(axis=0)
    normalized = composite_matrix / col_sum
    weights = normalized.mean(axis=1)

    aw = composite_matrix @ weights
    lambda_max = (aw / weights).mean()

    ci = (lambda_max - n) / (n - 1) if n > 1 else 0
    ri_values = [0, 0, 0.58, 0.90, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49]
    ri = ri_values[n] if n < len(ri_values) else 1.49
    cr = ci / ri if ri != 0 else 0

    return weights, cr


def compute_entropy_weights(data_matrix: np.ndarray) -> np.ndarray:
    m, n = data_matrix.shape
    col_sums = data_matrix.sum(axis=0)
    p = data_matrix / (col_sums + np.finfo(float).eps)
    k = 1.0 / np.log(m)
    e = -k * (p * np.log(p + np.finfo(float).eps)).sum(axis=0)
    d = 1 - e
    weights = d / d.sum()
    return weights


def compute_combined_weights(w_ahp: np.ndarray, w_entropy: np.ndarray, alpha: float) -> np.ndarray:
    combined = alpha * w_ahp + (1 - alpha) * w_entropy
    return combined / combined.sum()


def normalize_for_scoring(X: np.ndarray, is_benefit: np.ndarray) -> np.ndarray:
    m, n = X.shape
    Xn = np.zeros((m, n))

    is_binary = np.zeros(n, dtype=bool)
    for j in range(n):
        col = X[:, j]
        valid = col[~np.isnan(col)]
        if len(valid) > 0 and set(np.unique(valid).tolist()).issubset({0, 1}):
            is_binary[j] = True

    for j in range(n):
        x = X[:, j]
        if is_binary[j]:
            Xn[:, j] = x
            continue

        xmin = np.nanmin(x)
        xmax = np.nanmax(x)
        denom = xmax - xmin

        if not np.isfinite(denom) or denom == 0:
            Xn[:, j] = 0
        else:
            if is_benefit[j]:
                Xn[:, j] = (x - xmin) / denom
            else:
                Xn[:, j] = (xmax - x) / denom

    Xn[np.isnan(Xn)] = 0
    return Xn


def sort_warehouses_by_score(warehouse_ids: List[str], score_data: np.ndarray,
                             combined_weights: np.ndarray) -> Tuple[List[int], np.ndarray]:
    scores = score_data @ combined_weights
    sorted_indices = np.argsort(-scores)
    return sorted_indices.tolist(), scores


def correct_layer_order(sorted_indices: List[int], dam_ids: np.ndarray,
                        layer_ids: np.ndarray, warehouse_ids: List[str],
                        scores: np.ndarray) -> Tuple[List[int], np.ndarray, np.ndarray]:
    sorted_dam = dam_ids[sorted_indices]
    sorted_layer = layer_ids[sorted_indices]

    u_dam = np.unique(sorted_dam[~np.isnan(sorted_dam)])

    for d in u_dam:
        idx = [i for i in range(len(sorted_dam)) if sorted_dam[i] == d]
        if len(idx) <= 1:
            continue

        local_order = sorted(idx, key=lambda i: sorted_layer[i])
        new_idx = [sorted_indices[i] for i in local_order]

        for k, orig_pos in enumerate(idx):
            sorted_indices[orig_pos] = new_idx[k]

    sorted_dam = dam_ids[sorted_indices]
    sorted_layer = layer_ids[sorted_indices]

    return sorted_indices, sorted_dam, sorted_layer


def elevation_constraint_sort(sorted_indices: List[int], dam_ids: np.ndarray,
                              layer_ids: np.ndarray, score_indicators: np.ndarray,
                              base_elev_const: float, adj_limit: float,
                              global_limit: float,
                              dam_list_a: List[int] = None,
                              heights_a: List[float] = None) -> List[int]:
    n = len(sorted_indices)
    H_all = base_elev_const - score_indicators[:, 0]
    H_sorted = H_all[sorted_indices]

    u_dam = np.unique(dam_ids[sorted_indices][~np.isnan(dam_ids[sorted_indices])])
    n_dam = len(u_dam)

    dam_index_map = {int(d): k for k, d in enumerate(u_dam)}

    dam_index_row = np.full(n, -1, dtype=int)
    for i in range(n):
        d = dam_ids[sorted_indices[i]]
        if not np.isnan(d) and int(d) in dam_index_map:
            dam_index_row[i] = dam_index_map[int(d)]

    current_h = np.full(n_dam, np.nan)

    if dam_list_a and heights_a:
        for k, d in enumerate(u_dam):
            d_int = int(d)
            if d_int in dam_list_a:
                idx_a = dam_list_a.index(d_int)
                if idx_a < len(heights_a) and not np.isnan(heights_a[idx_a]):
                    current_h[k] = heights_a[idx_a]

    # 调试日志：输出A段初始高程和相邻高差
    import logging
    logger = logging.getLogger('scheduling')
    logger.info(f"[高差约束] 坝段列表: {u_dam.tolist()}")
    logger.info(f"[高差约束] A段初始高程: { {int(u_dam[k]): current_h[k] for k in range(n_dam) if not np.isnan(current_h[k])} }")
    for k in range(n_dam - 1):
        if not np.isnan(current_h[k]) and not np.isnan(current_h[k + 1]):
            diff = abs(current_h[k] - current_h[k + 1])
            logger.info(f"[高差约束] 相邻坝段 {int(u_dam[k])}-{int(u_dam[k+1])}: 高差={diff:.1f}m, 限制={adj_limit}m, {'违反' if diff > adj_limit else '满足'}")
    h_init = current_h[~np.isnan(current_h)]
    if len(h_init) >= 2:
        logger.info(f"[高差约束] 全局高差: {h_init.max() - h_init.min():.1f}m, 限制={global_limit}m, {'违反' if h_init.max()-h_init.min() > global_limit else '满足'}")

    # 自适应高差约束：检测A段初始高程中已违反约束的相邻坝段对，
    # 将其约束阈值放宽到实际高差值，避免后续排仓被已违反的约束卡死
    adaptive_adj_limit = np.full(n_dam, adj_limit)
    adj_relaxed_count = 0
    for k in range(n_dam - 1):
        if not np.isnan(current_h[k]) and not np.isnan(current_h[k + 1]):
            actual_diff = abs(current_h[k] - current_h[k + 1])
            if actual_diff > adj_limit:
                # 该相邻对的约束放宽到实际高差值，允许后续仓位不超过此差距
                adaptive_adj_limit[k] = max(adaptive_adj_limit[k], actual_diff)
                adaptive_adj_limit[k + 1] = max(adaptive_adj_limit[k + 1], actual_diff)
                adj_relaxed_count += 1
                logger.info(f"[高差约束] 自适应放宽: 坝段{int(u_dam[k])}限制{adj_limit}→{adaptive_adj_limit[k]:.1f}m, 坝段{int(u_dam[k+1])}限制{adj_limit}→{adaptive_adj_limit[k+1]:.1f}m")

    # 自适应全局约束：如果A段初始高程已超过全局限制，放宽到实际范围
    h_init = current_h[~np.isnan(current_h)]
    adaptive_global_limit = global_limit
    if len(h_init) >= 2:
        actual_global_diff = h_init.max() - h_init.min()
        if actual_global_diff > global_limit:
            adaptive_global_limit = actual_global_diff
            logger.info(f"[高差约束] 自适应放宽全局限制: {global_limit}→{adaptive_global_limit:.1f}m")

    if adj_relaxed_count == 0:
        logger.info(f"[高差约束] A段初始高程未违反约束，自适应机制未触发")
    
    # 调试日志：输出B段仓位高程和约束检查过程
    forced_count = 0

    # 记录每个坝段已排入的最大层号，确保同坝段内按层号递增浇筑
    dam_max_layer_placed = {}

    # 构建每个坝段内所有仓位按层号排序的映射，确定每个坝段下一个应该排入的层号
    dam_next_layer = {}  # {dam_id: next_layer_id_to_place}
    dam_all_layers = {}  # {dam_id: sorted list of layer_ids}
    for i in range(n):
        di = dam_index_row[i]
        if di >= 0:
            d_id = int(u_dam[di])
            if d_id not in dam_all_layers:
                dam_all_layers[d_id] = set()
            dam_all_layers[d_id].add(layer_ids[sorted_indices[i]])

    for d_id in dam_all_layers:
        dam_all_layers[d_id] = sorted(dam_all_layers[d_id])
        dam_next_layer[d_id] = dam_all_layers[d_id][0]  # 从最小层号开始

    used = np.zeros(n, dtype=bool)
    final_order = []

    for pos in range(n):
        placed = False
        chosen = -1

        for i in range(n):
            if used[i]:
                continue

            di = dam_index_row[i]
            Hi = H_sorted[i]

            if di < 0 or np.isnan(Hi):
                placed = True
                chosen = i
                break

            # 检查同坝段内层号顺序约束：当前仓位必须是该坝段下一个待排层号
            d_id = int(u_dam[di])
            current_layer = layer_ids[sorted_indices[i]]
            if d_id in dam_next_layer and current_layer != dam_next_layer[d_id]:
                continue  # 跳过：该仓位不是下一个应排入的层号

            temp_h = current_h.copy()
            temp_h[di] = Hi

            ok = True

            if di - 1 >= 0:
                Hj = temp_h[di - 1]
                if not np.isnan(Hj) and not np.isnan(temp_h[di]):
                    # 使用自适应的相邻高差限制
                    limit = max(adaptive_adj_limit[di], adaptive_adj_limit[di - 1])
                    if abs(temp_h[di] - Hj) > limit:
                        ok = False

            if ok and di + 1 <= n_dam - 1:
                Hj = temp_h[di + 1]
                if not np.isnan(Hj) and not np.isnan(temp_h[di]):
                    limit = max(adaptive_adj_limit[di], adaptive_adj_limit[di + 1])
                    if abs(temp_h[di] - Hj) > limit:
                        ok = False

            if ok:
                h_non_na = temp_h[~np.isnan(temp_h)]
                if len(h_non_na) > 0:
                    if h_non_na.max() - h_non_na.min() > adaptive_global_limit:
                        ok = False

            if ok:
                placed = True
                chosen = i
                current_h = temp_h
                # 更新坝段下一个待排层号
                d_id = int(u_dam[di])
                current_layer = layer_ids[sorted_indices[i]]
                if d_id in dam_max_layer_placed and current_layer > dam_max_layer_placed[d_id]:
                    dam_max_layer_placed[d_id] = current_layer
                elif d_id not in dam_max_layer_placed:
                    dam_max_layer_placed[d_id] = current_layer
                # 推进下一个待排层号
                if d_id in dam_next_layer:
                    layers = dam_all_layers[d_id]
                    idx_in_layers = layers.index(current_layer)
                    if idx_in_layers + 1 < len(layers):
                        dam_next_layer[d_id] = layers[idx_in_layers + 1]
                    else:
                        del dam_next_layer[d_id]  # 该坝段所有层号已排完
                break

        if not placed:
            chosen = int(np.where(~used)[0][0])
            di = dam_index_row[chosen]
            Hi = H_sorted[chosen]
            if di >= 0 and not np.isnan(Hi):
                current_h[di] = Hi
                forced_count += 1
                # 更新坝段层号记录
                d_id = int(u_dam[di])
                current_layer = layer_ids[sorted_indices[chosen]]
                if d_id not in dam_max_layer_placed or current_layer > dam_max_layer_placed[d_id]:
                    dam_max_layer_placed[d_id] = current_layer
                # 推进下一个待排层号
                if d_id in dam_next_layer:
                    layers = dam_all_layers[d_id]
                    idx_in_layers = layers.index(current_layer)
                    if idx_in_layers + 1 < len(layers):
                        dam_next_layer[d_id] = layers[idx_in_layers + 1]
                    else:
                        del dam_next_layer[d_id]
                # 强制排入后，动态更新自适应约束阈值
                # 如果强制排入导致新的高差违反，放宽对应坝段的约束
                for neighbor_di in [di - 1, di + 1]:
                    if 0 <= neighbor_di < n_dam and not np.isnan(current_h[neighbor_di]):
                        actual_diff = abs(current_h[di] - current_h[neighbor_di])
                        if actual_diff > adaptive_adj_limit[di]:
                            adaptive_adj_limit[di] = actual_diff
                            logger.info(f"[高差约束] 动态放宽: 坝段{int(u_dam[di])}限制→{adaptive_adj_limit[di]:.1f}m")
                        if actual_diff > adaptive_adj_limit[neighbor_di]:
                            adaptive_adj_limit[neighbor_di] = actual_diff
                            logger.info(f"[高差约束] 动态放宽: 坝段{int(u_dam[neighbor_di])}限制→{adaptive_adj_limit[neighbor_di]:.1f}m")
                # 更新全局约束
                h_now = current_h[~np.isnan(current_h)]
                if len(h_now) >= 2:
                    actual_global = h_now.max() - h_now.min()
                    if actual_global > adaptive_global_limit:
                        adaptive_global_limit = actual_global
                        logger.info(f"[高差约束] 动态放宽全局限制→{adaptive_global_limit:.1f}m")
                logger.warning(f"[高差约束] 强制排入(第{pos+1}步): 坝段{int(u_dam[di]) if di < n_dam else '?'} 高程={Hi:.1f}m")

        final_order.append(sorted_indices[chosen])
        used[chosen] = True

    logger.info(f"[高差约束] 排仓完成: 总仓位={n}, 强制排入={forced_count}次")
    return final_order


def extract_dam_ids(warehouse_ids: List[str]) -> np.ndarray:
    result = []
    for wid in warehouse_ids:
        parts = wid.split('-')
        try:
            result.append(int(parts[0]))
        except (ValueError, IndexError):
            result.append(np.nan)
    return np.array(result, dtype=float)


def extract_layer_ids(warehouse_ids: List[str]) -> np.ndarray:
    result = []
    for wid in warehouse_ids:
        parts = wid.split('-')
        try:
            result.append(int(parts[1]))
        except (ValueError, IndexError):
            result.append(np.nan)
    return np.array(result, dtype=float)


class CraneScheduler:
    def __init__(self, config: SchedulingConfig):
        self.config = config

    def schedule_by_crane_and_gap(self, sorted_report: pd.DataFrame,
                                  start_date: datetime, mode: str = 'normal') -> pd.DataFrame:
        n_rows = len(sorted_report)
        day_index = np.zeros(n_rows, dtype=int)
        used_crane = {}
        dam_last_end_day = {}

        crane_col = None
        rest_col = None
        for col in sorted_report.columns:
            if '缆机' in col or 'crane' in col.lower():
                crane_col = col
            if '间歇' in col or '间隔' in col or 'rest' in col.lower():
                rest_col = col

        if crane_col is None:
            crane_col = sorted_report.columns[2] if len(sorted_report.columns) > 2 else sorted_report.columns[-2]
        if rest_col is None:
            rest_col = sorted_report.columns[3] if len(sorted_report.columns) > 3 else sorted_report.columns[-1]

        rest_ref_vec = np.full(n_rows, np.nan)
        gap_new_vec = np.full(n_rows, np.nan)

        # 跟踪每个坝段首次出现的序号，用于让不同坝段第一仓错开开始
        dam_first_order = {}
        first_dam_count = 0

        for i in range(n_rows):
            wid = str(sorted_report.iloc[i]['WarehouseID'])
            nums = ''.join(filter(str.isdigit, wid.split('-')[0])) if '-' in wid else ''
            dam_id = int(nums) if nums else np.nan

            crane_need = sorted_report.iloc[i][crane_col]
            try:
                if isinstance(crane_need, (pd.Timedelta, timedelta)):
                    crane_need = crane_need.days if hasattr(crane_need, 'days') else 1
                if not np.isfinite(crane_need) or crane_need <= 0:
                    crane_need = 1
                crane_need = int(crane_need)
            except (TypeError, ValueError):
                crane_need = 1

            rest_ref = sorted_report.iloc[i][rest_col]
            try:
                if isinstance(rest_ref, (pd.Timedelta, timedelta)):
                    rest_ref = rest_ref.days if hasattr(rest_ref, 'days') else self.config.min_gap_days
                if not np.isfinite(rest_ref) or rest_ref <= 0:
                    rest_ref = self.config.min_gap_days
                rest_ref = float(rest_ref)
            except (TypeError, ValueError):
                rest_ref = float(self.config.min_gap_days)

            rest_ref_vec[i] = rest_ref

            if np.isnan(dam_id) or dam_id not in dam_last_end_day:
                # 不同坝段的第一仓按排序顺序错开1天，避免都从同一天开始
                if not np.isnan(dam_id):
                    if dam_id not in dam_first_order:
                        dam_first_order[dam_id] = first_dam_count
                        first_dam_count += 1
                    start_day = 1 + dam_first_order[dam_id]
                else:
                    start_day = 1
                day = self._find_earliest_day(used_crane, crane_need, start_day)
                gap_new_vec[i] = np.nan
            else:
                last_end_day = dam_last_end_day[dam_id]

                gap_target = rest_ref
                if gap_target < self.config.min_gap_days:
                    gap_target = self.config.min_gap_days
                if gap_target > self.config.max_gap_days:
                    gap_target = self.config.max_gap_days
                low_day = last_end_day + self.config.min_gap_days
                high_day = last_end_day + self.config.max_gap_days
                target_day = last_end_day + gap_target

                if mode == 'compress':
                    day = self._find_earliest_day(used_crane, crane_need, low_day)
                else:
                    day = self._choose_day_in_window(used_crane, crane_need,
                                                     target_day, low_day, high_day)

                gap_new = day - last_end_day
                gap_new_vec[i] = gap_new

            day_index[i] = day
            used_crane[day] = used_crane.get(day, 0) + crane_need

            if not np.isnan(dam_id):
                dam_last_end_day[dam_id] = day + 1

        start_dates = [start_date + timedelta(days=int(d) - 1) for d in day_index]
        end_dates = [d + timedelta(days=1) for d in start_dates]

        result = pd.DataFrame({
            'WarehouseID': sorted_report['WarehouseID'].values,
            '开始时间': start_dates,
            '结束时间': end_dates,
            '参考间歇时间_天': rest_ref_vec,
            '实际间隔_天': gap_new_vec
        })

        return result

    def _find_earliest_day(self, used_crane: dict, crane_need: int, start_day: int) -> int:
        day = start_day
        while True:
            if used_crane.get(day, 0) + crane_need <= self.config.max_crane_per_day:
                return day
            day += 1

    def _choose_day_in_window(self, used_crane: dict, crane_need: int,
                              target_day: int, low_day: int, high_day: int) -> int:
        best_day = None
        best_dist = float('inf')

        for day in range(low_day, high_day + 1):
            if used_crane.get(day, 0) + crane_need <= self.config.max_crane_per_day:
                dist = abs(day - target_day)
                if dist < best_dist:
                    best_dist = dist
                    best_day = day

        if best_day is None:
            day = high_day + 1
            while True:
                if used_crane.get(day, 0) + crane_need <= self.config.max_crane_per_day:
                    return day
                day += 1

        return best_day


class WinterScheduleHandler:
    def __init__(self, config: SchedulingConfig):
        self.config = config

    def apply_winter_to_schedule(self, schedule_df: pd.DataFrame) -> pd.DataFrame:
        result = schedule_df.copy()

        if len(result) == 0:
            return result

        has_rest_col = '参考间歇时间_天' in result.columns

        warehouse_ids = result['WarehouseID'].astype(str).tolist()
        dam_groups = {}
        for i, wid in enumerate(warehouse_ids):
            parts = wid.split('-')
            dam_id = parts[0] if len(parts) >= 1 else '0'
            if dam_id not in dam_groups:
                dam_groups[dam_id] = []
            dam_groups[dam_id].append(i)

        for dam_id, row_indices in dam_groups.items():
            if len(row_indices) == 0:
                continue

            dam_rows = result.iloc[row_indices].copy()
            start_times = pd.to_datetime(dam_rows['开始时间'])
            sorted_local = start_times.argsort().values

            prev_end = None
            for rank in range(len(sorted_local)):
                local_idx = sorted_local[rank]
                orig_row = row_indices[local_idx]

                orig_s = pd.Timestamp(result.iloc[orig_row]['开始时间'])
                orig_e = pd.Timestamp(result.iloc[orig_row]['结束时间'])
                dur = orig_e - orig_s

                if rank == 0:
                    candidate = orig_s
                else:
                    if has_rest_col:
                        rest_val = result.iloc[orig_row]['参考间歇时间_天']
                        try:
                            gap = float(rest_val)
                            if not np.isfinite(gap) or gap <= 0:
                                gap = self.config.min_gap_days
                        except (TypeError, ValueError):
                            gap = self.config.min_gap_days
                        if gap < self.config.min_gap_days:
                            gap = self.config.min_gap_days
                        if gap > self.config.max_gap_days:
                            gap = self.config.max_gap_days
                    else:
                        gap = self.config.min_gap_days

                    earliest_after_gap = prev_end + pd.Timedelta(days=int(round(gap)))
                    candidate = max(orig_s, earliest_after_gap)

                candidate = self._shift_out_of_winter(candidate)

                new_end = candidate + dur
                result.iloc[orig_row, result.columns.get_loc('开始时间')] = candidate
                result.iloc[orig_row, result.columns.get_loc('结束时间')] = new_end
                prev_end = new_end

        return result

    def _shift_out_of_winter(self, t) -> pd.Timestamp:
        t = pd.Timestamp(t)

        while True:
            y = t.year

            w1_start = pd.Timestamp(year=y - 1, month=self.config.winter_start_month,
                                    day=self.config.winter_start_day)
            w1_end = pd.Timestamp(year=y, month=self.config.winter_end_month,
                                  day=self.config.winter_end_day)

            w2_start = pd.Timestamp(year=y, month=self.config.winter_start_month,
                                    day=self.config.winter_start_day)
            w2_end = pd.Timestamp(year=y + 1, month=self.config.winter_end_month,
                                  day=self.config.winter_end_day)

            if w1_start <= t <= w1_end:
                t = w1_end + pd.Timedelta(days=1)
            elif w2_start <= t <= w2_end:
                t = w2_end + pd.Timedelta(days=1)
            else:
                break

        return t

    def is_winter_day(self, d) -> bool:
        d = pd.Timestamp(d)
        m = d.month
        dd = d.day
        if m >= 11:
            return True
        if m <= 3:
            return True
        if m == 4 and dd <= 10:
            return True
        return False

    def next_open_day(self, d) -> pd.Timestamp:
        d = pd.Timestamp(d).normalize()
        while self.is_winter_day(d):
            d = d + pd.Timedelta(days=1)
        return d

    def count_open_days(self, d0, d1) -> int:
        d0 = pd.Timestamp(d0).normalize()
        d1 = pd.Timestamp(d1).normalize()
        if d1 <= d0:
            return 0
        n = 0
        cur = d0
        while cur < d1:
            if not self.is_winter_day(cur):
                n += 1
            cur = cur + pd.Timedelta(days=1)
        return n

    def add_open_days(self, d, n_days) -> pd.Timestamp:
        d2 = self.next_open_day(d)
        n_days = int(round(n_days))
        if n_days <= 0:
            return d2
        moved = 0
        while moved < n_days:
            d2 = d2 + pd.Timedelta(days=1)
            if not self.is_winter_day(d2):
                moved += 1
        return d2


def build_complete_schedule(schedule_table: pd.DataFrame, a_idx: List[int],
                            b_idx: List[int], c_idx: List[int],
                            base_df: pd.DataFrame, act_df: pd.DataFrame,
                            config: SchedulingConfig) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    n_base = len(base_df)
    dam_plan = base_df['DamID'].values
    layer_plan = base_df['LayerID'].values
    plan_start = pd.to_datetime(base_df['PlanStart'])
    plan_end = pd.to_datetime(base_df['PlanEnd'])

    warehouse_id_plan = [f"{int(d)}-{int(l)}" for d, l in zip(dam_plan, layer_plan)]

    segment = ['C'] * n_base
    for i in a_idx:
        segment[i] = 'A'
    for i in b_idx:
        segment[i] = 'B'

    top_elev = base_df['TopElev'].values if 'TopElev' in base_df.columns else np.full(n_base, np.nan)

    t_all = pd.DataFrame({
        'WarehouseID': warehouse_id_plan,
        'DamID': dam_plan,
        'LayerID': layer_plan,
        'TopElev': top_elev,
        'PlanStart': plan_start.values,
        'PlanEnd': plan_end.values,
        'Segment': segment,
        'FinalStart': plan_start.values.copy(),
        'FinalEnd': plan_end.values.copy()
    })

    warehouse_id_act = []
    if len(act_df) > 0 and 'DamID' in act_df.columns and 'LayerID' in act_df.columns:
        act_dam = act_df['DamID'].values
        act_layer = act_df['LayerID'].values
        warehouse_id_act = [f"{int(d)}-{int(l)}" for d, l in zip(act_dam, act_layer)]

        act_start = pd.to_datetime(act_df['ActualStart']) if 'ActualStart' in act_df.columns else None
        act_end = pd.to_datetime(act_df['ActualEnd']) if 'ActualEnd' in act_df.columns else None

        for i in range(n_base):
            if segment[i] != 'A':
                continue
            wid = warehouse_id_plan[i]
            if wid in warehouse_id_act:
                act_pos = warehouse_id_act.index(wid)
                if act_start is not None and act_pos < len(act_start):
                    t_all.iloc[i, t_all.columns.get_loc('FinalStart')] = act_start.iloc[act_pos]
                if act_end is not None and act_pos < len(act_end):
                    t_all.iloc[i, t_all.columns.get_loc('FinalEnd')] = act_end.iloc[act_pos]

    wb_id = schedule_table['WarehouseID'].astype(str).tolist()
    wb_s = pd.to_datetime(schedule_table['开始时间'])
    wb_e = pd.to_datetime(schedule_table['结束时间'])

    for i in range(n_base):
        if segment[i] != 'B':
            continue
        wid = warehouse_id_plan[i]
        if wid in wb_id:
            b_pos = wb_id.index(wid)
            t_all.iloc[i, t_all.columns.get_loc('FinalStart')] = wb_s.iloc[b_pos]
            t_all.iloc[i, t_all.columns.get_loc('FinalEnd')] = wb_e.iloc[b_pos]

    is_b_mask = t_all['Segment'] == 'B'
    if is_b_mask.any():
        plan_end_b_max = pd.to_datetime(t_all.loc[is_b_mask, 'PlanEnd']).max()
        new_end_b_max = pd.to_datetime(t_all.loc[is_b_mask, 'FinalEnd']).max()
        delta = new_end_b_max - plan_end_b_max
    else:
        delta = pd.Timedelta(days=0)

    t_all = reschedule_c_with_winter(t_all, is_b_mask, delta, config)

    idx_all = list(range(n_base))
    idx_a = [i for i in idx_all if segment[i] == 'A']
    idx_b = [i for i in idx_all if segment[i] == 'B']
    idx_c = [i for i in idx_all if segment[i] == 'C']

    if idx_a and len(act_df) > 0 and warehouse_id_act:
        def sort_key_a(i):
            wid = warehouse_id_plan[i]
            if wid in warehouse_id_act:
                return warehouse_id_act.index(wid)
            return float('inf')
        idx_a.sort(key=sort_key_a)

    if idx_b and wb_id:
        def sort_key_b(i):
            wid = warehouse_id_plan[i]
            if wid in wb_id:
                return wb_id.index(wid)
            return float('inf')
        idx_b.sort(key=sort_key_b)

    final_order = idx_a + idx_b + idx_c
    if len(final_order) == n_base:
        t_all = t_all.iloc[final_order].reset_index(drop=True)

    is_a_sorted = t_all['Segment'] == 'A'
    is_c_sorted = t_all['Segment'] == 'C'
    t_a_out = t_all[is_a_sorted][['WarehouseID', 'DamID', 'LayerID', 'FinalStart', 'FinalEnd']].copy()
    t_c_out = t_all[is_c_sorted][['WarehouseID', 'DamID', 'LayerID', 'FinalStart', 'FinalEnd']].copy()

    return t_all, t_a_out, t_c_out


def reschedule_c_with_winter(t_all: pd.DataFrame, is_b_mask: pd.Series,
                             delta: pd.Timedelta, config: SchedulingConfig) -> pd.DataFrame:
    winter_handler = WinterScheduleHandler(config)
    is_c_all = t_all['Segment'] == 'C'
    idx_c = np.where(is_c_all)[0]

    if len(idx_c) == 0:
        return t_all

    plan_start_c = pd.to_datetime(t_all.iloc[idx_c]['PlanStart']).dt.normalize()
    plan_end_c = pd.to_datetime(t_all.iloc[idx_c]['PlanEnd']).dt.normalize()

    unique_days = plan_start_c.unique()
    unique_days = pd.Series(unique_days).sort_values().tolist()

    c_base_start = plan_start_c.min()

    new_base_start = (c_base_start + delta).normalize()
    new_base_start = winter_handler.next_open_day(new_base_start)

    batch_offset_days = {}
    for batch_day in unique_days:
        batch_offset_days[batch_day] = winter_handler.count_open_days(c_base_start, batch_day)

    # 收集A/B段各坝段末仓时间，用于约束C段首仓不得早于已浇筑末仓+间歇
    dam_last_end = {}
    if 'Segment' in t_all.columns:
        for seg in ['A', 'B']:
            seg_mask = t_all['Segment'] == seg
            if seg_mask.any():
                seg_df = t_all[seg_mask]
                for _, row in seg_df.iterrows():
                    d = int(row['DamID']) if not pd.isna(row.get('DamID')) else None
                    if d is None:
                        continue
                    end_t = pd.to_datetime(row['FinalEnd'], errors='coerce')
                    if pd.isna(end_t):
                        continue
                    if d not in dam_last_end or end_t > dam_last_end[d]:
                        dam_last_end[d] = end_t

    gap_days = max(int(config.min_gap_days), 1)

    from collections import defaultdict

    for batch_day in unique_days:
        batch_new_start = winter_handler.add_open_days(new_base_start, batch_offset_days[batch_day])

        rows = idx_c[plan_start_c.values == batch_day]
        rows_list = rows.tolist() if hasattr(rows, 'tolist') else list(rows)

        # 按(坝段, 层号)排序，保证同坝段内层号顺序
        rows_sorted = sorted(
            rows_list,
            key=lambda r: (int(t_all.iloc[r]['DamID']) if not pd.isna(t_all.iloc[r]['DamID']) else 0,
                           int(t_all.iloc[r]['LayerID']) if not pd.isna(t_all.iloc[r]['LayerID']) else 0)
        )

        # 按坝段分组，同坝段仓面串行排程，不同坝段首仓错开1天
        dam_groups = defaultdict(list)
        for r in rows_sorted:
            d = int(t_all.iloc[r]['DamID']) if not pd.isna(t_all.iloc[r]['DamID']) else 0
            dam_groups[d].append(r)

        dam_offset = 0
        for dam_id in sorted(dam_groups.keys()):
            dam_rows = dam_groups[dam_id]
            current_start = winter_handler.add_open_days(batch_new_start, dam_offset)

            # C段首仓不得早于已浇筑/已排B段末仓 + 间歇
            if dam_id in dam_last_end:
                min_start = winter_handler.add_open_days(dam_last_end[dam_id], gap_days)
                if current_start < min_start:
                    current_start = min_start

            for r in dam_rows:
                i_row = r
                dur_days = (pd.Timestamp(t_all.iloc[i_row]['PlanEnd']).normalize() -
                            pd.Timestamp(t_all.iloc[i_row]['PlanStart']).normalize()).days
                if dur_days < 0 or pd.isna(dur_days):
                    dur_days = 0

                t_all.iloc[i_row, t_all.columns.get_loc('FinalStart')] = current_start
                current_end = winter_handler.add_open_days(current_start, dur_days)
                t_all.iloc[i_row, t_all.columns.get_loc('FinalEnd')] = current_end

                # 同坝段下一仓 = 本仓结束 + 间歇
                current_start = winter_handler.add_open_days(current_end, gap_days)

            dam_offset += 1

    return t_all


def build_owner_export_table(t_source: pd.DataFrame) -> pd.DataFrame:
    col_names = ['编号', '坝段号', '仓号', '仓顶高程(m)', '计划结束时间', '计划开始时间', '新排仓开始时间', '新排仓结束时间']

    if t_source is None or len(t_source) == 0:
        return pd.DataFrame(columns=col_names)

    n = len(t_source)
    t_export = pd.DataFrame()
    t_export['编号'] = t_source['WarehouseID'].values
    t_export['坝段号'] = t_source['DamID'].values
    t_export['仓号'] = t_source['LayerID'].values
    if 'TopElev' in t_source.columns:
        t_export['仓顶高程(m)'] = pd.to_numeric(t_source['TopElev'], errors='coerce').round(2).values
    else:
        t_export['仓顶高程(m)'] = [None] * n
    t_export['计划结束时间'] = _format_date_column(t_source['PlanEnd'])
    t_export['计划开始时间'] = _format_date_column(t_source['PlanStart'])
    t_export['新排仓开始时间'] = _format_date_column(t_source['FinalStart'])
    t_export['新排仓结束时间'] = _format_date_column(t_source['FinalEnd'])

    t_export.columns = col_names
    return t_export


def _format_date_column(series) -> List[str]:
    result = []
    for v in series:
        if pd.isna(v):
            result.append('')
        else:
            try:
                dt = pd.Timestamp(v)
                result.append(dt.strftime('%Y/%m/%d'))
            except:
                result.append('')
    return result


def get_fixed_monthly_window(ref_date=None):
    if ref_date is not None:
        today = pd.Timestamp(ref_date)
    else:
        today = pd.Timestamp.now()
    d = today.day
    y = today.year
    m = today.month

    if d >= 26:
        win_start = today.replace(day=26)
        next_month = win_start + pd.DateOffset(months=1)
        win_end = next_month.replace(day=25)
    else:
        this_month_start = today.replace(day=1)
        prev_month = this_month_start - pd.DateOffset(months=1)
        win_start = prev_month.replace(day=26)
        win_end = today.replace(day=25)

    return win_start, win_end


def get_next_fixed_monthly_window(ref_date=None):
    current_start, current_end = get_fixed_monthly_window(ref_date)
    next_start = current_end + pd.Timedelta(days=1)
    next_end = next_start + (current_end - current_start)
    return next_start, next_end


def get_rolling_window(t_all: pd.DataFrame):
    is_b = t_all['Segment'] == 'B'
    if is_b.any():
        rolling_start = pd.Timestamp(t_all.loc[is_b, 'FinalStart'].min()).normalize()
    else:
        is_not_a = t_all['Segment'] != 'A'
        if is_not_a.any():
            rolling_start = pd.Timestamp(t_all.loc[is_not_a, 'FinalStart'].min()).normalize()
        else:
            rolling_start = pd.Timestamp(t_all['FinalStart'].min()).normalize()

    y = rolling_start.year
    m = rolling_start.month
    d = rolling_start.day

    next_y = y
    next_m = m + 1
    if next_m > 12:
        next_m = 1
        next_y = y + 1

    import calendar
    last_day_next_month = calendar.monthrange(next_y, next_m)[1]
    same_day_next_month = min(d, last_day_next_month)
    next_month_same_day = pd.Timestamp(year=next_y, month=next_m, day=same_day_next_month)
    rolling_end = (next_month_same_day - pd.Timedelta(days=1)).normalize()

    return rolling_start, rolling_end


def filter_table_by_overlap(t_all: pd.DataFrame, win_start, win_end) -> pd.DataFrame:
    if t_all is None or len(t_all) == 0:
        return pd.DataFrame()
    if 'FinalStart' not in t_all.columns or 'FinalEnd' not in t_all.columns:
        return pd.DataFrame()
    final_start = pd.to_datetime(t_all['FinalStart'])
    final_end = pd.to_datetime(t_all['FinalEnd'])

    mask = (final_start <= win_end) & (final_end >= win_start)
    t_sub = t_all[mask].copy()
    if len(t_sub) > 0:
        t_sub = t_sub.sort_values('FinalStart').reset_index(drop=True)
    return t_sub


def export_plan_windows(t_all: pd.DataFrame, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    today = pd.Timestamp.now()

    fixed_start, fixed_end = get_fixed_monthly_window(today)
    t_fixed = filter_table_by_overlap(t_all, fixed_start, fixed_end)
    t_fixed_export = build_owner_export_table(t_fixed)
    fixed_file = os.path.join(output_dir, f'月计划_固定周期_{fixed_start.strftime("%Y%m%d")}-{fixed_end.strftime("%Y%m%d")}.xlsx')
    t_fixed_export.to_excel(fixed_file, index=False, sheet_name='固定周期月计划')

    rolling_start, rolling_end = get_rolling_window(t_all)
    t_rolling = filter_table_by_overlap(t_all, rolling_start, rolling_end)
    t_rolling_export = build_owner_export_table(t_rolling)
    rolling_file = os.path.join(output_dir, f'月计划_滚动周期_{rolling_start.strftime("%Y%m%d")}-{rolling_end.strftime("%Y%m%d")}.xlsx')
    t_rolling_export.to_excel(rolling_file, index=False, sheet_name='滚动周期月计划')

    year_start = pd.Timestamp(year=today.year, month=1, day=1)
    year_end = pd.Timestamp(year=today.year, month=12, day=31)
    t_year = filter_table_by_overlap(t_all, year_start, year_end)
    t_year_export = build_owner_export_table(t_year)
    year_file = os.path.join(output_dir, f'年计划_{today.year}.xlsx')
    t_year_export.to_excel(year_file, index=False, sheet_name='年计划')

    return {
        'fixed': fixed_file,
        'rolling': rolling_file,
        'year': year_file,
        'fixed_count': len(t_fixed),
        'rolling_count': len(t_rolling),
        'year_count': len(t_year),
        'fixed_window_start': str(fixed_start),
        'fixed_window_end': str(fixed_end),
        'rolling_window_start': str(rolling_start),
        'rolling_window_end': str(rolling_end)
    }


import os


DAM_CREST_ELEV = 990.0  # 大坝坝顶高程


def _estimate_elev_for_layer(dam_id: int, layer_id: int, elev_lookup: dict) -> float:
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


def _load_dam_elev_file_lookup() -> dict:
    """从 DamElevation.xlsx 加载完整的高程查找表作为基础参考"""
    import os
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dam_elev_file = os.path.join(base_dir, 'uploads', 'DamElevation.xlsx')
        if not os.path.exists(dam_elev_file):
            return {}
        dam_elev_df = pd.read_excel(dam_elev_file)
        lookup = {}
        for _, er in dam_elev_df.iterrows():
            d = int(er['DamID']) if not pd.isna(er.get('DamID')) else None
            l = int(er['LayerID']) if not pd.isna(er.get('LayerID')) else None
            e = float(er['TopElev']) if not pd.isna(er.get('TopElev')) else None
            if d is not None and l is not None and e is not None:
                lookup[(d, l)] = float(e)
        return lookup
    except Exception:
        return {}


# 全局缓存DamElevation.xlsx的高程查找表（只加载一次）
_DAM_ELEV_FILE_LOOKUP_CACHE = None


def _get_dam_elev_file_lookup() -> dict:
    global _DAM_ELEV_FILE_LOOKUP_CACHE
    if _DAM_ELEV_FILE_LOOKUP_CACHE is None:
        _DAM_ELEV_FILE_LOOKUP_CACHE = _load_dam_elev_file_lookup()
    return _DAM_ELEV_FILE_LOOKUP_CACHE


def _build_elev_lookup_from_df(df: pd.DataFrame) -> dict:
    # 先用 DamElevation.xlsx 的完整高程数据作为基础
    lookup = dict(_get_dam_elev_file_lookup())
    if df is None or len(df) == 0 or 'TopElev' not in df.columns:
        return lookup
    # 再用传入的df中的真实TopElev覆盖（有实际浇筑记录的高程更准确）
    for _, row in df.iterrows():
        dam_id = int(row['DamID']) if not pd.isna(row.get('DamID')) else None
        layer_id = int(row['LayerID']) if not pd.isna(row.get('LayerID')) else None
        elev = row.get('TopElev')
        if dam_id is not None and layer_id is not None and not pd.isna(elev):
            lookup[(dam_id, layer_id)] = float(elev)
    return lookup


def build_cross_tab_data(t_all: pd.DataFrame) -> dict:
    if t_all is None or len(t_all) == 0:
        return {'available': False}

    df = t_all.copy()
    df['DamID'] = df['DamID'].astype(int)
    df['LayerID'] = df['LayerID'].astype(int)

    if 'TopElev' in df.columns:
        df['TopElev'] = pd.to_numeric(df['TopElev'], errors='coerce')
    else:
        df['TopElev'] = np.nan

    df['FinalStart'] = pd.to_datetime(df['FinalStart'])
    df['FinalEnd'] = pd.to_datetime(df['FinalEnd'])

    dams = sorted(df['DamID'].unique().tolist())

    elev_lookup = _build_elev_lookup_from_df(df)

    dam_layers = {}
    for dam_id in dams:
        dam_df = df[df['DamID'] == dam_id].copy()
        dam_df = dam_df.sort_values('TopElev', ascending=False, na_position='last')
        dam_df = dam_df.sort_values('LayerID', ascending=False, kind='mergesort')
        total_layers = len(dam_df)
        layers = []
        for row_idx, (_, row) in enumerate(dam_df.iterrows()):
            elev = row['TopElev']
            if pd.isna(elev):
                elev = _estimate_elev_for_layer(dam_id, int(row['LayerID']), elev_lookup)
            start_time = row['FinalStart']
            if isinstance(start_time, pd.Timestamp):
                start_time = start_time.strftime('%Y-%m-%d')
            # 序号从下往上编号：底层=1，顶层=total_layers
            order_num = total_layers - row_idx
            layers.append({
                'elevation': round(float(elev), 2),
                'layerId': int(row['LayerID']),
                'segment': str(row['Segment']),
                'startTime': start_time,
                'warehouseId': str(row['WarehouseID']),
                'orderNum': order_num,
            })
        dam_layers[dam_id] = layers

    all_elevations = set()
    for dam_id in dams:
        for layer in dam_layers[dam_id]:
            all_elevations.add(layer['elevation'])
    sorted_elevations = sorted(all_elevations, reverse=True)

    max_layers = max(len(v) for v in dam_layers.values()) if dam_layers else 0

    return {
        'available': True,
        'dams': dams,
        'damLayers': {str(k): v for k, v in dam_layers.items()},
        'sortedElevations': sorted_elevations,
        'maxLayers': max_layers,
        'totalWarehouses': len(df),
    }


def build_cross_tab_export(t_all: pd.DataFrame, output_path: str) -> str:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    if t_all is None or len(t_all) == 0:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '大坝仓位总排仓计划表'
        wb.save(output_path)
        return output_path

    df = t_all.copy()
    df['DamID'] = df['DamID'].astype(int)
    df['LayerID'] = df['LayerID'].astype(int)

    if 'TopElev' in df.columns:
        df['TopElev'] = pd.to_numeric(df['TopElev'], errors='coerce')
    else:
        df['TopElev'] = np.nan

    df['FinalStart'] = pd.to_datetime(df['FinalStart'])
    df['FinalEnd'] = pd.to_datetime(df['FinalEnd'])

    dams = sorted(df['DamID'].unique().tolist())

    elev_lookup = _build_elev_lookup_from_df(df)

    dam_data = {}
    for dam_id in dams:
        dam_df = df[df['DamID'] == dam_id].copy()
        dam_df = dam_df.sort_values('TopElev', ascending=False, na_position='last')
        dam_df = dam_df.sort_values('LayerID', ascending=False, kind='mergesort')
        dam_data[dam_id] = dam_df

    # 按高程对齐：收集所有仓面的TopElev，从高到低排序，每行对应一个高程
    all_elevations_set = set()
    for dam_id in dams:
        dam_df = dam_data[dam_id]
        for _, row in dam_df.iterrows():
            elev = row['TopElev']
            if pd.isna(elev):
                elev = _estimate_elev_for_layer(dam_id, int(row['LayerID']), elev_lookup)
            if not pd.isna(elev):
                all_elevations_set.add(round(float(elev), 2))

    # 从高到低排序（990在第一行，750在最后一行）
    all_elevs_desc = sorted(all_elevations_set, reverse=True)

    # 3m网格聚类：高程差<3m的仓面归入同一行（解决1.5m层高与3m层高交错导致的空白行）
    # 每个聚类取该组中的最大高程作为代表高程
    elev_clusters = []  # 列表 of (代表高程, [高程列表])
    elev_to_cluster_idx = {}
    for elev in all_elevs_desc:
        if elev_clusters and abs(elev_clusters[-1][0] - elev) < 3.0:
            # 归入当前聚类
            elev_clusters[-1][1].append(elev)
            # 代表高程取最大值（因为从高到低遍历，第一个就是最大值）
            # 不需要更新代表高程，因为已经是从高到低，第一个最大
        else:
            # 新起一个聚类
            elev_clusters.append((elev, [elev]))
        elev_to_cluster_idx[elev] = len(elev_clusters) - 1

    # sorted_elevations 是聚类后的代表高程列表（从高到低）
    sorted_elevations = [c[0] for c in elev_clusters]

    # 构建每个坝段在聚类代表高程->仓面信息的映射
    # 同聚类有多个仓面时（混合层高），保留层号最大的仓面（dam_df按LayerID降序，第一个是层号最大）
    dam_elev_map = {}
    for dam_id in dams:
        dam_df = dam_data[dam_id]
        rep_elev_to_row = {}
        for _, row in dam_df.iterrows():
            elev = row['TopElev']
            if pd.isna(elev):
                elev = _estimate_elev_for_layer(dam_id, int(row['LayerID']), elev_lookup)
            elev = round(float(elev), 2)
            cluster_idx = elev_to_cluster_idx.get(elev)
            if cluster_idx is None:
                continue
            rep_elev = sorted_elevations[cluster_idx]
            # 只保留第一个（层号最大），避免冲突覆盖
            if rep_elev not in rep_elev_to_row:
                rep_elev_to_row[rep_elev] = row
        dam_elev_map[dam_id] = rep_elev_to_row

    # 每个坝段从底部数起的序号（底层=1）
    dam_order_map = {}
    for dam_id in dams:
        dam_df = dam_data[dam_id]
        total_layers = len(dam_df)
        # dam_df 按TopElev降序、LayerID降序，反转后从底层开始
        rep_elev_to_order = {}
        for row_idx, (_, row) in enumerate(dam_df.iterrows()):
            elev = row['TopElev']
            if pd.isna(elev):
                elev = _estimate_elev_for_layer(dam_id, int(row['LayerID']), elev_lookup)
            elev = round(float(elev), 2)
            cluster_idx = elev_to_cluster_idx.get(elev)
            if cluster_idx is None:
                continue
            rep_elev = sorted_elevations[cluster_idx]
            # 只保留层号最大的仓面的序号
            if rep_elev not in rep_elev_to_order:
                rep_elev_to_order[rep_elev] = total_layers - row_idx
        dam_order_map[dam_id] = rep_elev_to_order

    max_rows = len(sorted_elevations)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '大坝仓位总排仓计划表'

    header_font = Font(name='等线', size=10, bold=True)
    data_font = Font(name='等线', size=10)
    center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)

    thin_border = Border(
        left=Side(style='thin', color='999999'),
        right=Side(style='thin', color='999999'),
        top=Side(style='thin', color='999999'),
        bottom=Side(style='thin', color='999999')
    )

    segment_a_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    segment_b_fill = PatternFill(start_color='BDD7EE', end_color='BDD7EE', fill_type='solid')
    segment_c_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

    for dam_idx, dam_id in enumerate(dams):
        start_col = dam_idx * 3 + 1
        end_col = start_col + 2

        ws.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=end_col)
        header_cell = ws.cell(row=1, column=start_col, value=f'{dam_id}坝段')
        header_cell.font = header_font
        header_cell.alignment = center_align
        header_cell.border = thin_border

        sub_headers = ['高程', '序号', '开仓时间']
        for sub_idx, sub_h in enumerate(sub_headers):
            cell = ws.cell(row=2, column=start_col + sub_idx, value=sub_h)
            cell.font = Font(name='等线', size=9, bold=True)
            cell.alignment = center_align
            cell.border = thin_border

        dam_df = dam_data[dam_id]
        elev_to_row = dam_elev_map.get(dam_id, {})
        elev_to_order = dam_order_map.get(dam_id, {})

        # 按sorted_elevations顺序填充，每行对应一个聚类代表高程
        for row_idx, rep_elev in enumerate(sorted_elevations):
            data_row = row_idx + 3

            row = elev_to_row.get(rep_elev)
            if row is None:
                continue

            order_num = elev_to_order.get(rep_elev, 0)

            start_time = row['FinalStart']
            if isinstance(start_time, pd.Timestamp):
                start_time = start_time.strftime('%Y-%m-%d')
            else:
                start_time = str(start_time)[:10]

            segment = str(row['Segment'])

            # 显示聚类代表高程（让同行所有坝段高程值一致）
            elev_cell = ws.cell(row=data_row, column=start_col, value=rep_elev)
            order_cell = ws.cell(row=data_row, column=start_col + 1, value=order_num)
            time_cell = ws.cell(row=data_row, column=start_col + 2, value=start_time)

            for cell in [elev_cell, order_cell, time_cell]:
                cell.font = data_font
                cell.alignment = center_align
                cell.border = thin_border

            if segment == 'A':
                fill = segment_a_fill
            elif segment == 'B':
                fill = segment_b_fill
            else:
                fill = segment_c_fill

            for cell in [elev_cell, order_cell, time_cell]:
                cell.fill = fill

    for dam_idx in range(len(dams)):
        col_base = dam_idx * 3 + 1
        ws.column_dimensions[get_column_letter(col_base)].width = 8
        ws.column_dimensions[get_column_letter(col_base + 1)].width = 6
        ws.column_dimensions[get_column_letter(col_base + 2)].width = 12

    ws.row_dimensions[1].height = 20
    ws.row_dimensions[2].height = 18

    ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)

    wb.save(output_path)
    return output_path


@dataclass
class ScheduleCompressionConfig:
    use_compression: bool = False
    water_storage_date: str = '2028/10/01'
    water_storage_elevation: float = 920.0
    completion_date: str = '2030/10/15'
    compress_interval: bool = True
    interval_min: int = 14
    interval_max: int = 20
    interval_reduction: int = 1
    critical_path_first: bool = True


class ScheduleCompressor:
    def __init__(self, config: ScheduleCompressionConfig, base_config: SchedulingConfig):
        self.config = config
        self.base_config = base_config

    def _build_dam_map(self, schedule_df: pd.DataFrame) -> dict:
        dam_map = {}
        warehouse_ids = schedule_df['WarehouseID'].astype(str).tolist()
        for i, wid in enumerate(warehouse_ids):
            parts = wid.split('-')
            dam_id = parts[0] if len(parts) >= 1 else '0'
            layer_id = int(parts[1]) if len(parts) >= 2 else 0
            if dam_id not in dam_map:
                dam_map[dam_id] = []
            dam_map[dam_id].append((layer_id, i))
        for dam_id in dam_map:
            dam_map[dam_id].sort(key=lambda x: x[0])
        return dam_map

    def compress_schedule(self, schedule_df: pd.DataFrame, base_df: pd.DataFrame,
                          b_idx: List[int], sorted_report: pd.DataFrame,
                          start_dt: datetime) -> Tuple[pd.DataFrame, dict]:
        original_end = pd.Timestamp(schedule_df['结束时间'].max()) if len(schedule_df) > 0 else None
        compressed = schedule_df.copy()

        compression_log = {
            'original_end_date': str(original_end) if original_end else '',
            'interval_compressed': 0,
            'critical_path_adjusted': False
        }

        if self.config.compress_interval:
            compressed, n_compressed = self._compress_intervals(compressed)
            compression_log['interval_compressed'] = n_compressed

        if self.config.critical_path_first:
            compressed = self._prioritize_critical_path(compressed, base_df, b_idx, start_dt)
            compression_log['critical_path_adjusted'] = True

        compressed_end = pd.Timestamp(compressed['结束时间'].max()) if len(compressed) > 0 else None
        compression_log['compressed_end_date'] = str(compressed_end) if compressed_end else ''

        if original_end and compressed_end:
            compression_log['saved_days'] = max(0, (original_end - compressed_end).days)
        else:
            compression_log['saved_days'] = 0

        return compressed, compression_log

    def _compress_intervals(self, schedule_df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        if len(schedule_df) == 0:
            return schedule_df, 0

        result = schedule_df.copy()
        n_compressed = 0
        dam_map = self._build_dam_map(result)

        for dam_id, layers in dam_map.items():
            if len(layers) <= 1:
                continue

            for k in range(1, len(layers)):
                prev_layer, prev_row = layers[k - 1]
                curr_layer, curr_row = layers[k]

                prev_end = pd.Timestamp(result.iloc[prev_row]['结束时间'])
                curr_start = pd.Timestamp(result.iloc[curr_row]['开始时间'])
                curr_end = pd.Timestamp(result.iloc[curr_row]['结束时间'])
                dur = curr_end - curr_start

                gap_days = (curr_start - prev_end).days

                if self.config.interval_min <= gap_days <= self.config.interval_max:
                    new_gap = max(self.base_config.min_gap_days,
                                  gap_days - self.config.interval_reduction)
                    if new_gap < gap_days:
                        new_start = prev_end + pd.Timedelta(days=new_gap)
                        new_end = new_start + dur

                        result.iloc[curr_row, result.columns.get_loc('开始时间')] = new_start
                        result.iloc[curr_row, result.columns.get_loc('结束时间')] = new_end
                        n_compressed += 1

        if n_compressed > 0:
            result = self._recascade_schedule(result)

        return result, n_compressed

    def _recascade_schedule(self, schedule_df: pd.DataFrame) -> pd.DataFrame:
        if len(schedule_df) == 0:
            return schedule_df

        result = schedule_df.copy()
        dam_map = self._build_dam_map(result)
        has_rest_col = '参考间歇时间_天' in result.columns

        for dam_id, layers in dam_map.items():
            for k in range(len(layers)):
                layer_id, row_idx = layers[k]

                orig_start = pd.Timestamp(result.iloc[row_idx]['开始时间'])
                orig_end = pd.Timestamp(result.iloc[row_idx]['结束时间'])
                dur = orig_end - orig_start

                min_start = None
                if k > 0:
                    prev_layer, prev_row = layers[k - 1]
                    prev_end = pd.Timestamp(result.iloc[prev_row]['结束时间'])

                    gap = self.base_config.min_gap_days
                    if has_rest_col:
                        rest_val = result.iloc[row_idx]['参考间歇时间_天']
                        try:
                            gap = float(rest_val)
                            if not np.isfinite(gap) or gap <= 0:
                                gap = self.base_config.min_gap_days
                        except (TypeError, ValueError):
                            gap = self.base_config.min_gap_days
                        if gap < self.base_config.min_gap_days:
                            gap = self.base_config.min_gap_days
                        if gap > self.base_config.max_gap_days:
                            gap = self.base_config.max_gap_days

                    min_start = prev_end + pd.Timedelta(days=int(round(gap)))

                if min_start is not None and orig_start < min_start:
                    result.iloc[row_idx, result.columns.get_loc('开始时间')] = min_start
                    result.iloc[row_idx, result.columns.get_loc('结束时间')] = min_start + dur

        return result

    def _prioritize_critical_path(self, schedule_df: pd.DataFrame,
                                   base_df: pd.DataFrame, b_idx: List[int],
                                   start_dt: datetime) -> pd.DataFrame:
        if len(schedule_df) == 0:
            return schedule_df

        water_storage_dt = datetime.strptime(self.config.water_storage_date, '%Y/%m/%d')
        completion_dt = datetime.strptime(self.config.completion_date, '%Y/%m/%d')
        target_elev = self.config.water_storage_elevation

        result = schedule_df.copy()
        has_rest_col = '参考间歇时间_天' in result.columns

        water_storage_critical = set()
        completion_critical = set()
        if 'TopElev' in base_df.columns:
            for idx in b_idx:
                row = base_df.iloc[idx]
                elev = row.get('TopElev')
                if pd.notna(elev):
                    wid = f"{int(row['DamID'])}-{int(row['LayerID'])}"
                    if float(elev) <= target_elev:
                        water_storage_critical.add(wid)
                    else:
                        completion_critical.add(wid)

        if not water_storage_critical and not completion_critical:
            return result

        def _get_gap_for_row(row_idx):
            if has_rest_col:
                rest_val = result.iloc[row_idx]['参考间歇时间_天']
                try:
                    g = float(rest_val)
                    if not np.isfinite(g) or g <= 0:
                        g = self.base_config.min_gap_days
                except (TypeError, ValueError):
                    g = self.base_config.min_gap_days
                if g < self.base_config.min_gap_days:
                    g = self.base_config.min_gap_days
                if g > self.base_config.max_gap_days:
                    g = self.base_config.max_gap_days
                return g
            return self.base_config.min_gap_days

        warehouse_ids = result['WarehouseID'].astype(str).tolist()
        wid_to_row = {}
        for i, wid in enumerate(warehouse_ids):
            wid_to_row[wid] = i

        dam_map = self._build_dam_map(result)
        dam_layer_map = {}
        for dam_id, layers in dam_map.items():
            for layer_id, row_idx in layers:
                wid = warehouse_ids[row_idx]
                if dam_id not in dam_layer_map:
                    dam_layer_map[dam_id] = {}
                dam_layer_map[dam_id][layer_id] = row_idx

        for wid in water_storage_critical:
            if wid not in wid_to_row:
                continue
            ci = wid_to_row[wid]
            orig_start = pd.Timestamp(result.iloc[ci]['开始时间'])
            orig_end = pd.Timestamp(result.iloc[ci]['结束时间'])
            dur = orig_end - orig_start

            if orig_end <= pd.Timestamp(water_storage_dt):
                continue

            parts = wid.split('-')
            dam_id = parts[0] if len(parts) >= 1 else '0'
            layer_id = int(parts[1]) if len(parts) >= 2 else 0

            min_start = start_dt + pd.Timedelta(days=1)
            if dam_id in dam_layer_map:
                prev_layers = [l for l in dam_layer_map[dam_id] if l < layer_id]
                if prev_layers:
                    prev_layer = max(prev_layers)
                    prev_row = dam_layer_map[dam_id][prev_layer]
                    prev_end = pd.Timestamp(result.iloc[prev_row]['结束时间'])
                    gap = _get_gap_for_row(ci)
                    min_start = prev_end + pd.Timedelta(days=int(round(gap)))

            if min_start < orig_start:
                result.iloc[ci, result.columns.get_loc('开始时间')] = min_start
                result.iloc[ci, result.columns.get_loc('结束时间')] = min_start + dur

        result = self._recascade_schedule(result)

        warehouse_ids = result['WarehouseID'].astype(str).tolist()
        wid_to_row = {}
        for i, wid in enumerate(warehouse_ids):
            wid_to_row[wid] = i

        dam_map = self._build_dam_map(result)
        dam_layer_map = {}
        for dam_id, layers in dam_map.items():
            for layer_id, row_idx in layers:
                wid = warehouse_ids[row_idx]
                if dam_id not in dam_layer_map:
                    dam_layer_map[dam_id] = {}
                dam_layer_map[dam_id][layer_id] = row_idx

        for wid in completion_critical:
            if wid not in wid_to_row:
                continue
            ci = wid_to_row[wid]
            orig_start = pd.Timestamp(result.iloc[ci]['开始时间'])
            orig_end = pd.Timestamp(result.iloc[ci]['结束时间'])
            dur = orig_end - orig_start

            if orig_end <= pd.Timestamp(completion_dt):
                continue

            parts = wid.split('-')
            dam_id = parts[0] if len(parts) >= 1 else '0'
            layer_id = int(parts[1]) if len(parts) >= 2 else 0

            min_start = start_dt + pd.Timedelta(days=1)
            if dam_id in dam_layer_map:
                prev_layers = [l for l in dam_layer_map[dam_id] if l < layer_id]
                if prev_layers:
                    prev_layer = max(prev_layers)
                    prev_row = dam_layer_map[dam_id][prev_layer]
                    prev_end = pd.Timestamp(result.iloc[prev_row]['结束时间'])
                    gap = _get_gap_for_row(ci)
                    min_start = prev_end + pd.Timedelta(days=int(round(gap)))

            if min_start < orig_start:
                result.iloc[ci, result.columns.get_loc('开始时间')] = min_start
                result.iloc[ci, result.columns.get_loc('结束时间')] = min_start + dur

        result = self._recascade_schedule(result)
        return result

    def check_constraints(self, t_all: pd.DataFrame) -> dict:
        water_storage_dt = pd.Timestamp(datetime.strptime(self.config.water_storage_date, '%Y/%m/%d'))
        completion_dt = pd.Timestamp(datetime.strptime(self.config.completion_date, '%Y/%m/%d'))
        target_elev = self.config.water_storage_elevation

        water_storage_satisfied = True
        if 'TopElev' in t_all.columns and 'FinalEnd' in t_all.columns:
            low_elev_mask = pd.to_numeric(t_all['TopElev'], errors='coerce') <= target_elev
            if low_elev_mask.any():
                low_elev_end = pd.to_datetime(t_all.loc[low_elev_mask, 'FinalEnd']).max()
                if low_elev_end > water_storage_dt:
                    water_storage_satisfied = False

        completion_satisfied = True
        if 'TopElev' in t_all.columns and 'FinalEnd' in t_all.columns:
            high_elev_mask = pd.to_numeric(t_all['TopElev'], errors='coerce') > target_elev
            if high_elev_mask.any():
                high_elev_end = pd.to_datetime(t_all.loc[high_elev_mask, 'FinalEnd']).max()
                if high_elev_end > completion_dt:
                    completion_satisfied = False

        final_end = pd.to_datetime(t_all['FinalEnd']).max() if len(t_all) > 0 else None

        return {
            'water_storage_satisfied': water_storage_satisfied,
            'water_storage_date': self.config.water_storage_date,
            'water_storage_elevation': target_elev,
            'completion_satisfied': completion_satisfied,
            'completion_date': self.config.completion_date,
            'actual_end_date': str(final_end) if final_end else ''
        }
