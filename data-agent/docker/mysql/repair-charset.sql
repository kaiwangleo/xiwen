SET NAMES utf8mb4;

UPDATE dim_region SET province = '北京', region_name = '华北', country = '中国' WHERE region_id = 'R01';
UPDATE dim_region SET province = '上海', region_name = '华东', country = '中国' WHERE region_id = 'R02';
UPDATE dim_region SET province = '广东', region_name = '华南', country = '中国' WHERE region_id = 'R03';
UPDATE dim_region SET province = '湖北', region_name = '华中', country = '中国' WHERE region_id = 'R04';
UPDATE dim_region SET province = '四川', region_name = '西南', country = '中国' WHERE region_id = 'R05';

UPDATE dim_customer SET customer_name = '张三', gender = '男', member_level = '黄金' WHERE customer_id = 'C01';
UPDATE dim_customer SET customer_name = '李四', gender = '女', member_level = '白银' WHERE customer_id = 'C02';
UPDATE dim_customer SET customer_name = '王五', gender = '男', member_level = '钻石' WHERE customer_id = 'C03';
UPDATE dim_customer SET customer_name = '赵六', gender = '女', member_level = '黄金' WHERE customer_id = 'C04';
UPDATE dim_customer SET customer_name = '钱七', gender = '男', member_level = '普通' WHERE customer_id = 'C05';

UPDATE dim_product SET product_name = '奥利奥巧克力夹心饼干', category = '零食', brand = '奥利奥' WHERE product_id = 'P01';
UPDATE dim_product SET product_name = '蒙牛纯牛奶 250ml*12', category = '乳品', brand = '蒙牛' WHERE product_id = 'P02';
UPDATE dim_product SET product_name = '乐事原味薯片 150g', category = '零食', brand = '乐事' WHERE product_id = 'P03';
UPDATE dim_product SET product_name = '雀巢金牌速溶咖啡', category = '饮料', brand = '雀巢' WHERE product_id = 'P04';
