import csv
import os

# --- 配置 ---
# 请将 vehicle_functions.csv 文件与此脚本放在同一目录下
CSV_FILE_PATH = 'vehicle_functions.csv'
OUTPUT_SQL_FILE = 'import_product_features.sql'
TABLE_NAME = 'product_features'

def escape_sql_string(value):
    """一个简单的SQL字符串转义函数"""
    if value is None:
        return "NULL"
    # 将单引号替换为两个单引号来转义
    return "'" + str(value).replace("'", "''") + "'"

def generate_sql_from_csv():
    """
    读取CSV文件并生成用于导入product_features表的SQL语句。
    """
    if not os.path.exists(CSV_FILE_PATH):
        print(f"错误: 未找到CSV文件 '{CSV_FILE_PATH}'。请确保文件存在于脚本同一目录下。")
        return

    # 用于存储所有生成的INSERT语句
    sql_statements = []

    try:
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # 从CSV行中提取数据并去除首尾空格
                feature_code = row.get('id', '').strip()
                parent_code = row.get('父级功能', '').strip()
                feature_name = row.get('功能名称', '').strip()
                feature_description = row.get('功能说明与用户视角', '').strip()
                hierarchy_level = row.get('hierarchy_level', '').strip()

                # 跳过没有ID的无效行
                if not feature_code or not hierarchy_level:
                    continue

                # --- 处理父级ID ---
                # 如果父级功能编码为空，则parent_id_fk为NULL
                # 否则，我们生成一个子查询来动态获取父级的自增ID
                if parent_code:
                    parent_id_fk_sql = f"(SELECT pf.product_feature_id FROM {TABLE_NAME} pf WHERE pf.feature_code = {escape_sql_string(parent_code)})"
                else:
                    parent_id_fk_sql = "NULL"

                # --- 构建INSERT语句 ---
                # 注意：我们不插入product_feature_id，因为它会自动增长
                sql = (
                    f"INSERT INTO `{TABLE_NAME}` "
                    f"(`feature_code`, `feature_name`, `feature_description`, `parent_id_fk`, `hierarchy_level`) "
                    f"VALUES ("
                    f"{escape_sql_string(feature_code)}, "
                    f"{escape_sql_string(feature_name)}, "
                    f"{escape_sql_string(feature_description)}, "
                    f"{parent_id_fk_sql}, "
                    f"{int(hierarchy_level)}"
                    f");"
                )
                sql_statements.append(sql)

        # --- 写入到SQL文件 ---
        with open(OUTPUT_SQL_FILE, mode='w', encoding='utf-8') as sqlfile:
            sqlfile.write("-- =================================================================\n")
            sqlfile.write(f"--  SQL Import Script for {TABLE_NAME} Table\n")
            sqlfile.write(f"--  Generated from: {CSV_FILE_PATH}\n")
            sqlfile.write("-- =================================================================\n\n")
            
            # 为了确保子查询能找到父级，我们需要按层级排序插入
            # 但由于CSV本身已按层级排序，此处直接写入即可。
            # 如果CSV顺序混乱，需要更复杂的逻辑来重新排序语句。
            for statement in sql_statements:
                sqlfile.write(statement + "\n")

        print(f"成功！已生成SQL导入文件：'{OUTPUT_SQL_FILE}'")
        print(f"共包含 {len(sql_statements)} 条INSERT语句。")

    except FileNotFoundError:
        print(f"错误: 文件未找到 - {CSV_FILE_PATH}")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")

if __name__ == '__main__':
    generate_sql_from_csv()