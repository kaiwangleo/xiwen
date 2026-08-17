SET NAMES utf8mb4;
USE dw;

CREATE TABLE IF NOT EXISTS dim_region (
    region_id   VARCHAR(20)  NOT NULL,
    province    VARCHAR(50)  NOT NULL,
    region_name VARCHAR(50)  NOT NULL,
    country     VARCHAR(50)  NOT NULL,
    PRIMARY KEY (region_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id   VARCHAR(20) NOT NULL,
    customer_name VARCHAR(50) NOT NULL,
    gender        VARCHAR(10) NOT NULL,
    member_level  VARCHAR(20) NOT NULL,
    PRIMARY KEY (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS dim_product (
    product_id   VARCHAR(20)  NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    category     VARCHAR(50)  NOT NULL,
    brand        VARCHAR(50)  NOT NULL,
    PRIMARY KEY (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS dim_date (
    date_id INT         NOT NULL,
    year    INT         NOT NULL,
    quarter VARCHAR(2)  NOT NULL,
    month   INT         NOT NULL,
    day     INT         NOT NULL,
    PRIMARY KEY (date_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fact_order (
    order_id       VARCHAR(30)    NOT NULL,
    customer_id    VARCHAR(20)    NOT NULL,
    product_id     VARCHAR(20)    NOT NULL,
    date_id        INT            NOT NULL,
    region_id      VARCHAR(20)    NOT NULL,
    order_quantity INT            NOT NULL,
    order_amount   FLOAT          NOT NULL,
    PRIMARY KEY (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO dim_region (region_id, province, region_name, country) VALUES
('R01', '北京', '华北', '中国'),
('R02', '上海', '华东', '中国'),
('R03', '广东', '华南', '中国'),
('R04', '湖北', '华中', '中国'),
('R05', '四川', '西南', '中国');

INSERT INTO dim_customer (customer_id, customer_name, gender, member_level) VALUES
('C01', '张三', '男', '黄金'),
('C02', '李四', '女', '白银'),
('C03', '王五', '男', '钻石'),
('C04', '赵六', '女', '黄金'),
('C05', '钱七', '男', '普通');

INSERT INTO dim_product (product_id, product_name, category, brand) VALUES
('P01', '奥利奥巧克力夹心饼干', '零食', '奥利奥'),
('P02', '蒙牛纯牛奶 250ml*12', '乳品', '蒙牛'),
('P03', '乐事原味薯片 150g', '零食', '乐事'),
('P04', '雀巢金牌速溶咖啡', '饮料', '雀巢');

INSERT INTO dim_date (date_id, year, quarter, month, day)
SELECT
    CAST(DATE_FORMAT(d, '%Y%m%d') AS UNSIGNED) AS date_id,
    YEAR(d) AS year,
    CONCAT('Q', QUARTER(d)) AS quarter,
    MONTH(d) AS month,
    DAY(d) AS day
FROM (
    SELECT DATE('2025-01-01') + INTERVAL seq DAY AS d
    FROM (
        SELECT a.n + b.n * 10 + c.n * 100 + d.n * 1000 AS seq
        FROM
            (SELECT 0 n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a,
            (SELECT 0 n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) b,
            (SELECT 0 n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) c,
            (SELECT 0 n UNION SELECT 1) d
    ) nums
    WHERE DATE('2025-01-01') + INTERVAL seq DAY <= DATE('2026-08-17')
) dates;

INSERT INTO fact_order (order_id, customer_id, product_id, date_id, region_id, order_quantity, order_amount) VALUES
('O20250301001', 'C01', 'P01', 20250301, 'R02', 40, 320.00),
('O20250315002', 'C02', 'P02', 20250315, 'R02', 20, 180.00),
('O20250408003', 'C03', 'P03', 20250408, 'R02', 18, 90.00),
('O20250520004', 'C04', 'P01', 20250520, 'R02', 35, 280.00),
('O20250611005', 'C05', 'P04', 20250611, 'R02', 8, 96.00),
('O20250703006', 'C01', 'P02', 20250703, 'R01', 12, 108.00),
('O20250819007', 'C02', 'P03', 20250819, 'R01', 15, 75.00),
('O20250922008', 'C03', 'P04', 20250922, 'R01', 6, 72.00),
('O20251005009', 'C04', 'P01', 20251005, 'R03', 22, 176.00),
('O20251118010', 'C05', 'P03', 20251118, 'R03', 25, 125.00),
('O20251202011', 'C01', 'P04', 20251202, 'R03', 10, 120.00),
('O20250120012', 'C02', 'P02', 20250120, 'R04', 16, 144.00),
('O20250214013', 'C03', 'P03', 20250214, 'R04', 12, 60.00),
('O20250426014', 'C04', 'P01', 20250426, 'R05', 18, 144.00),
('O20250608015', 'C05', 'P02', 20250608, 'R05', 30, 270.00),
('O20250830016', 'C01', 'P01', 20250830, 'R05', 10, 80.00),
('O20260301017', 'C01', 'P01', 20260301, 'R02', 25, 200.00),
('O20260312018', 'C02', 'P02', 20260312, 'R02', 25, 225.00),
('O20260405019', 'C03', 'P03', 20260405, 'R02', 17, 85.00),
('O20260518020', 'C04', 'P04', 20260518, 'R01', 9, 108.00),
('O20260622021', 'C05', 'P03', 20260622, 'R01', 12, 60.00),
('O20260709022', 'C01', 'P02', 20260709, 'R03', 14, 126.00),
('O20260801023', 'C02', 'P01', 20260801, 'R03', 26, 208.00),
('O20260810024', 'C03', 'P04', 20260810, 'R04', 7, 84.00),
('O20260115025', 'C04', 'P02', 20260115, 'R05', 26, 234.00);
