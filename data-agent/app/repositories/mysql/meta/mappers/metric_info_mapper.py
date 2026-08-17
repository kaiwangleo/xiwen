from dataclasses import asdict

from app.models.metric_info_mysql import MetricInfoMySQL


class MetricInfoMapper:
    @staticmethod
    def to_model(entity) -> MetricInfoMySQL:
        """实体转 ORM，供批量写入 metric_info。"""
        return MetricInfoMySQL(**asdict(entity))
