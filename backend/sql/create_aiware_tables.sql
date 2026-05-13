-- =====================================================
-- AIWARE 数据库表结构
-- 拱坝智能排仓计划数据存储系统
-- 数据库: aiware
-- =====================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS aiware 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE aiware;

-- =====================================================
-- 1. 排仓运行记录表 (主表)
-- 存储每次排仓计算的元数据
-- =====================================================
CREATE TABLE IF NOT EXISTS scheduling_runs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '运行记录ID',
    run_id VARCHAR(50) NOT NULL UNIQUE COMMENT '运行标识 (如: Run_20260427_091850)',
    run_name VARCHAR(200) COMMENT '运行名称/备注',
    run_type ENUM('normal', 'compress', 'manual') DEFAULT 'normal' COMMENT '运行类型',
    
    -- 时间参数
    start_date DATE NOT NULL COMMENT '排仓开始日期',
    deadline_date DATE COMMENT '工期截止日期',
    actual_end_date DATE COMMENT '实际完成日期',
    
    -- 算法参数
    alpha DECIMAL(3,2) DEFAULT 0.50 COMMENT 'AHP权重系数',
    max_crane_per_day INT DEFAULT 4 COMMENT '每天最大缆机数',
    min_gap_days INT DEFAULT 7 COMMENT '最小间歇天数',
    max_gap_days INT DEFAULT 20 COMMENT '最大间歇天数',
    n_extra INT DEFAULT 10 COMMENT 'B段额外仓面数',
    
    -- 统计信息
    total_warehouses INT DEFAULT 0 COMMENT '总仓面数',
    count_a INT DEFAULT 0 COMMENT 'A段数量(已完成)',
    count_b INT DEFAULT 0 COMMENT 'B段数量(优化中)',
    count_c INT DEFAULT 0 COMMENT 'C段数量(未开始)',
    
    -- 状态
    status ENUM('running', 'completed', 'failed', 'cancelled') DEFAULT 'running' COMMENT '运行状态',
    progress_percent INT DEFAULT 0 COMMENT '进度百分比',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    
    -- 用户信息
    created_by VARCHAR(50) COMMENT '创建用户',
    
    INDEX idx_run_id (run_id),
    INDEX idx_start_date (start_date),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='排仓运行记录主表';


-- =====================================================
-- 2. 仓面计划详情表
-- 存储每个仓面的详细计划信息
-- =====================================================
CREATE TABLE IF NOT EXISTS warehouse_schedules (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    run_id VARCHAR(50) NOT NULL COMMENT '关联的运行ID',
    
    -- 仓面标识
    warehouse_id VARCHAR(50) NOT NULL COMMENT '仓面编号 (如: 15-23)',
    dam_id INT NOT NULL COMMENT '坝段号',
    layer_id INT NOT NULL COMMENT '层号',
    
    -- 分段信息
    segment ENUM('A', 'B', 'C') NOT NULL COMMENT 'ABC分段',
    segment_order INT COMMENT '段内排序',
    
    -- 高程信息
    top_elevation DECIMAL(10,2) COMMENT '仓顶高程(m)',
    bottom_elevation DECIMAL(10,2) COMMENT '仓底高程(m)',
    
    -- 计划时间 (基准计划)
    plan_start_date DATE COMMENT '计划开始日期',
    plan_end_date DATE COMMENT '计划结束日期',
    
    -- 实际/最终时间
    actual_start_date DATE COMMENT '实际开始日期 (A段)',
    actual_end_date DATE COMMENT '实际结束日期 (A段)',
    final_start_date DATE COMMENT '最终开始日期 (B/C段排仓结果)',
    final_end_date DATE COMMENT '最终结束日期 (B/C段排仓结果)',
    
    -- 状态
    status ENUM('planned', 'in_progress', 'completed', 'cancelled') DEFAULT 'planned' COMMENT '仓面状态',
    
    -- 评分数据
    score DECIMAL(10,6) COMMENT '综合得分',
    priority_rank INT COMMENT '优先级排序',
    
    -- 浇筑参数
    pouring_volume DECIMAL(10,2) COMMENT '浇筑方量(m³)',
    crane_count INT DEFAULT 1 COMMENT '所需缆机数',
    rest_days DECIMAL(5,2) COMMENT '间歇时间(天)',
    pouring_intensity DECIMAL(8,2) COMMENT '浇筑强度(m³/h)',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 外键和索引
    FOREIGN KEY (run_id) REFERENCES scheduling_runs(run_id) ON DELETE CASCADE,
    INDEX idx_run_warehouse (run_id, warehouse_id),
    INDEX idx_dam_layer (dam_id, layer_id),
    INDEX idx_segment (segment),
    INDEX idx_final_start (final_start_date),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仓面计划详情表';


-- =====================================================
-- 3. 月计划窗口表
-- 存储不同时间窗口的月计划
-- =====================================================
CREATE TABLE IF NOT EXISTS monthly_plans (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    run_id VARCHAR(50) NOT NULL COMMENT '关联的运行ID',
    
    -- 窗口类型
    window_type ENUM('fixed', 'next', 'rolling') NOT NULL COMMENT '窗口类型: 固定/下月/滚动',
    window_name VARCHAR(50) COMMENT '窗口名称',
    
    -- 时间范围
    window_start_date DATE NOT NULL COMMENT '窗口开始日期',
    window_end_date DATE NOT NULL COMMENT '窗口结束日期',
    
    -- 统计
    warehouse_count INT DEFAULT 0 COMMENT '仓面数量',
    count_a INT DEFAULT 0 COMMENT 'A段数量',
    count_b INT DEFAULT 0 COMMENT 'B段数量',
    count_c INT DEFAULT 0 COMMENT 'C段数量',
    
    -- 文件存储
    file_path VARCHAR(500) COMMENT '导出文件路径',
    file_name VARCHAR(200) COMMENT '导出文件名',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (run_id) REFERENCES scheduling_runs(run_id) ON DELETE CASCADE,
    INDEX idx_run_window (run_id, window_type),
    INDEX idx_window_dates (window_start_date, window_end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月计划窗口表';


-- =====================================================
-- 4. 月计划仓面关联表
-- 月计划与仓面的多对多关系
-- =====================================================
CREATE TABLE IF NOT EXISTS monthly_plan_warehouses (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    monthly_plan_id BIGINT NOT NULL COMMENT '月计划ID',
    warehouse_schedule_id BIGINT NOT NULL COMMENT '仓面计划ID',
    run_id VARCHAR(50) NOT NULL COMMENT '运行ID (冗余存储便于查询)',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (monthly_plan_id) REFERENCES monthly_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (warehouse_schedule_id) REFERENCES warehouse_schedules(id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES scheduling_runs(run_id) ON DELETE CASCADE,
    UNIQUE KEY uk_plan_warehouse (monthly_plan_id, warehouse_schedule_id),
    INDEX idx_run (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月计划仓面关联表';


-- =====================================================
-- 5. 权重配置表
-- 存储每次运行的AHP和熵权法权重
-- =====================================================
CREATE TABLE IF NOT EXISTS scheduling_weights (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    run_id VARCHAR(50) NOT NULL COMMENT '关联的运行ID',
    
    -- 指标名称
    indicator_name VARCHAR(50) NOT NULL COMMENT '指标名称',
    indicator_index INT COMMENT '指标序号',
    
    -- 权重值
    ahp_weight DECIMAL(8,6) COMMENT 'AHP权重',
    entropy_weight DECIMAL(8,6) COMMENT '熵权法权重',
    combined_weight DECIMAL(8,6) COMMENT '组合权重',
    
    -- 指标属性
    is_benefit BOOLEAN DEFAULT TRUE COMMENT '是否为正向指标',
    
    -- 一致性检验
    cr_value DECIMAL(6,4) COMMENT '一致性比率CR (仅第一条记录)',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (run_id) REFERENCES scheduling_runs(run_id) ON DELETE CASCADE,
    INDEX idx_run_indicator (run_id, indicator_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权重配置表';


-- =====================================================
-- 6. 系统配置表
-- 存储全局配置参数
-- =====================================================
CREATE TABLE IF NOT EXISTS system_configs (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '配置ID',
    config_key VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    config_type VARCHAR(20) DEFAULT 'string' COMMENT '值类型: string/int/float/bool/json',
    description VARCHAR(500) COMMENT '配置说明',
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';


-- =====================================================
-- 7. 数据同步日志表
-- 记录数据同步操作
-- =====================================================
CREATE TABLE IF NOT EXISTS sync_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    sync_type VARCHAR(50) NOT NULL COMMENT '同步类型: baseline/actual/elevation',
    source_table VARCHAR(100) COMMENT '源表名 (qbt数据库)',
    target_table VARCHAR(100) COMMENT '目标表名 (aiware数据库)',
    
    -- 同步信息
    records_count INT DEFAULT 0 COMMENT '同步记录数',
    status ENUM('success', 'failed', 'partial') COMMENT '同步状态',
    error_message TEXT COMMENT '错误信息',
    
    -- 时间戳
    sync_start_time TIMESTAMP COMMENT '同步开始时间',
    sync_end_time TIMESTAMP COMMENT '同步结束时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    INDEX idx_sync_type (sync_type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据同步日志表';


-- =====================================================
-- 插入默认配置
-- =====================================================
INSERT INTO system_configs (config_key, config_value, config_type, description) VALUES
('scheduling.alpha', '0.5', 'float', 'AHP权重系数'),
('scheduling.max_crane_per_day', '4', 'int', '每天最大缆机数'),
('scheduling.min_gap_days', '7', 'int', '最小间歇天数'),
('scheduling.max_gap_days', '20', 'int', '最大间歇天数'),
('scheduling.n_extra', '10', 'int', 'B段额外仓面数'),
('winter.start_month', '11', 'int', '冬歇开始月份'),
('winter.start_day', '1', 'int', '冬歇开始日期'),
('winter.end_month', '4', 'int', '冬歇结束月份'),
('winter.end_day', '10', 'int', '冬歇结束日期'),
('system.version', '2.0.0', 'string', '系统版本号')
ON DUPLICATE KEY UPDATE config_value = VALUES(config_value);
