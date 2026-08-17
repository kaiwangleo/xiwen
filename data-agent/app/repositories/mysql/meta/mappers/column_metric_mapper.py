from dataclasses import asdict

from app.models.column_metric_mysql import ColumnMetricMySQL


class ColumnMetricMapper:
    @staticmethod
    def to_model(column_metric) -> ColumnMetricMySQL:
        """实体转 ORM，供批量写入 column_metric。"""
        return ColumnMetricMySQL(**asdict(column_metric))
