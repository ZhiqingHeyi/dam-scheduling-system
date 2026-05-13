CREATE TABLE IF NOT EXISTS dam_elevation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dam_section INT NOT NULL COMMENT '坝段号',
    layer_no INT NOT NULL COMMENT '层号',
    top_elevation DECIMAL(10,2) NOT NULL COMMENT '仓顶高程(m)',
    bottom_elevation DECIMAL(10,2) GENERATED ALWAYS AS (top_elevation - 3) STORED COMMENT '仓底高程(m)',
    UNIQUE KEY uk_dam_layer (dam_section, layer_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='大坝各坝段各层高程数据';
