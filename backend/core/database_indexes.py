"""
数据库索引优化脚本
添加常用查询的索引以提高性能
"""
from sqlalchemy import text
from core.database import engine

# 需要创建的索引列表
INDEXES = [
    # 用户表索引
    ("users", "idx_users_membership", "membership_level"),
    ("users", "idx_users_created_at", "created_at"),

    # 检测记录表索引 - 复合索引
    ("detection_records", "idx_detection_user_created", "user_id, created_at DESC"),
    ("detection_records", "idx_detection_company", "company_name"),
    ("detection_records", "idx_detection_risk_level", "risk_level"),
    ("detection_records", "idx_detection_year", "year"),
    ("detection_records", "idx_detection_stock_code", "stock_code"),
    ("detection_records", "idx_detection_status", "status"),

    # 报告表索引
    ("reports", "idx_reports_record_id", "record_id"),
    ("reports", "idx_reports_share_token", "share_token"),

    # 订单表索引
    ("orders", "idx_orders_user_status", "user_id, status"),
    ("orders", "idx_orders_order_no", "order_no"),

    # 问答历史索引
    ("qa_history", "idx_qa_user_created", "user_id, created_at DESC"),
]


def create_indexes():
    """创建所有优化索引"""
    print("=" * 60)
    print("📊 数据库索引优化")
    print("=" * 60)

    with engine.connect() as connection:
        for table_name, index_name, columns in INDEXES:
            try:
                # 检查索引是否已存在
                check_sql = f"""
                SELECT COUNT(*) FROM information_schema.STATISTICS
                WHERE table_schema = DATABASE()
                AND table_name = '{table_name}'
                AND index_name = '{index_name}'
                """
                result = connection.execute(text(check_sql))
                exists = result.scalar() > 0

                if exists:
                    print(f"  ℹ️  索引已存在: {index_name}")
                    continue

                # 创建索引
                create_sql = f"CREATE INDEX {index_name} ON {table_name} ({columns})"
                connection.execute(text(create_sql))
                print(f"  ✅ 创建索引: {index_name} ON {table_name}({columns})")

            except Exception as e:
                print(f"  ⚠️  创建索引 {index_name} 失败: {e}")

        connection.commit()

    print("=" * 60)
    print("✅ 数据库索引优化完成")
    print("=" * 60)


def drop_indexes():
    """删除所有自定义索引（仅开发/测试使用）"""
    print("=" * 60)
    print("📊 删除数据库索引")
    print("=" * 60)

    with engine.connect() as connection:
        for table_name, index_name, columns in INDEXES:
            try:
                drop_sql = f"DROP INDEX IF EXISTS {index_name} ON {table_name}"
                connection.execute(text(drop_sql))
                print(f"  ✅ 删除索引: {index_name}")
            except Exception as e:
                print(f"  ⚠️  删除索引 {index_name} 失败: {e}")

        connection.commit()

    print("=" * 60)
    print("✅ 索引删除完成")
    print("=" * 60)


def show_indexes():
    """显示当前所有索引"""
    print("=" * 60)
    print("📊 当前数据库索引")
    print("=" * 60)

    with engine.connect() as connection:
        sql = """
        SELECT table_name, index_name, column_name
        FROM information_schema.STATISTICS
        WHERE table_schema = DATABASE()
        AND index_name != 'PRIMARY'
        ORDER BY table_name, index_name
        """
        result = connection.execute(text(sql))
        current_table = None
        current_index = None

        for row in result:
            if current_table != row[0]:
                current_table = row[0]
                print(f"\n📋 表: {current_table}")

            if current_index != row[1]:
                current_index = row[1]
                print(f"   └─ {row[1]}")

            print(f"      └─ {row[2]}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "create":
            create_indexes()
        elif sys.argv[1] == "drop":
            drop_indexes()
        elif sys.argv[1] == "show":
            show_indexes()
        else:
            print("用法: python database_indexes.py [create|drop|show]")
    else:
        create_indexes()
