from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DWMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_schema(self) -> list[dict]:
        """读当前库 information_schema，返回表+列（含注释和键类型）。"""
        tables_sql = text(
            """
            SELECT TABLE_NAME AS name,
                   IFNULL(TABLE_COMMENT, '') AS comment,
                   IFNULL(TABLE_ROWS, 0) AS table_rows
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """
        )
        tables = [dict(row) for row in (await self.session.execute(tables_sql)).mappings()]
        cols_sql = text(
            """
            SELECT TABLE_NAME AS table_name,
                   COLUMN_NAME AS name,
                   COLUMN_TYPE AS type,
                   COLUMN_KEY AS col_key,
                   IFNULL(COLUMN_COMMENT, '') AS comment,
                   DATA_TYPE AS data_type
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME, ORDINAL_POSITION
            """
        )
        by_table: dict[str, list[dict]] = {}
        for row in (await self.session.execute(cols_sql)).mappings():
            by_table.setdefault(row["table_name"], []).append(
                {
                    "name": row["name"],
                    "type": row["type"],
                    "col_key": row["col_key"] or "",
                    "comment": row["comment"] or "",
                    "data_type": row["data_type"] or "",
                }
            )
        return [
            {
                "name": item["name"],
                "comment": item["comment"] or "",
                "table_rows": int(item["table_rows"] or 0),
                "columns": by_table.get(item["name"], []),
            }
            for item in tables
        ]

    async def get_column_types(self, table_name: str) -> dict[str, str]:
        """取表字段类型映射。"""
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        return {row.Field: row.Type for row in result.fetchall()}

    async def get_column_values(self, table_name: str, column_name: str, limit: int):
        """取字段去重样例，limit 由构建步骤配置。"""
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return result.scalars().fetchall()

    async def get_db_info(self):
        """数仓版本与方言，拼给生成 SQL 的提示词。"""
        result = await self.session.execute(text("select version()"))
        version = result.scalar()

        dialect = self.session.get_bind().dialect.name

        return {'version': version, 'dialect': dialect}

    async def validate_sql(self, sql):
        """EXPLAIN 校验 SQL，非法则抛错。"""
        await self.session.execute(text(f"explain {sql}"))

    async def execute_sql(self, sql):
        """执行只读查询，返回 list[dict]。"""
        result = await self.session.execute(text(sql))
        return [dict(row) for row in result.mappings().fetchall()]
