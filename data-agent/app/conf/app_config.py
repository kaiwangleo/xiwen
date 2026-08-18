from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path

from omegaconf import OmegaConf

from app.conf.paths import APP_CONFIG_EXAMPLE_PATH, APP_CONFIG_PATH


@dataclass
class File:
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str


@dataclass
class Console:
    enable: bool
    level: str


@dataclass
class LoggingConfig:
    file: File
    console: Console


@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantCollections:
    column: str = "data-agent-column"
    metric: str = "data-agent-metric"


@dataclass
class QdrantSearch:
    score_threshold: float = 0.6
    limit: int = 5


@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int
    collections: QdrantCollections = field(default_factory=QdrantCollections)
    search: QdrantSearch = field(default_factory=QdrantSearch)


@dataclass
class EmbeddingConfig:
    host: str
    port: int
    model: str
    path: str = "/embed"
    timeout: int = 120
    batch_size: int = 10


@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str = "data-agent-value"


@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    base_url: str
    temperature: float = 0
    timeout: int = 120


@dataclass
class LoadConfigStep:
    enabled: bool = True


@dataclass
class SaveTablesStep:
    enabled: bool = True
    example_limit: int = 10


@dataclass
class IndexColumnsStep:
    enabled: bool = True
    batch_size: int = 10


@dataclass
class IndexValuesStep:
    enabled: bool = True
    value_limit: int = 100000


@dataclass
class SaveMetricsStep:
    enabled: bool = True


@dataclass
class IndexMetricsStep:
    enabled: bool = True
    batch_size: int = 10


@dataclass
class KnowledgeBuildSteps:
    load_config: LoadConfigStep = field(default_factory=LoadConfigStep)
    save_tables: SaveTablesStep = field(default_factory=SaveTablesStep)
    index_columns: IndexColumnsStep = field(default_factory=IndexColumnsStep)
    index_values: IndexValuesStep = field(default_factory=IndexValuesStep)
    save_metrics: SaveMetricsStep = field(default_factory=SaveMetricsStep)
    index_metrics: IndexMetricsStep = field(default_factory=IndexMetricsStep)


@dataclass
class KnowledgeBuildConfig:
    on_error: str = "abort"
    steps: KnowledgeBuildSteps = field(default_factory=KnowledgeBuildSteps)


@dataclass
class ChartConfig:
    default: str = "auto"
    thousand_separator: bool = True


def _default_quick_asks() -> list[str]:
    """问数页空状态的默认推荐问。"""
    return [
        "统计去年各地区的销售总额",
        "黄金会员的平均客单价",
        "零食类商品销量排行",
    ]


@dataclass
class UIConfig:
    show_sql: bool = True
    quick_asks: list[str] = field(default_factory=_default_quick_asks)


@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig
    knowledge_build: KnowledgeBuildConfig = field(default_factory=KnowledgeBuildConfig)
    chart: ChartConfig = field(default_factory=ChartConfig)
    ui: UIConfig = field(default_factory=UIConfig)


config_file = APP_CONFIG_PATH
config_example_file = APP_CONFIG_EXAMPLE_PATH


def config_source_file() -> Path:
    """Prefer the ignored local config and fall back to the committed example."""
    return config_file if config_file.is_file() else config_example_file


def load_app_config() -> AppConfig:
    """从 YAML 加载运行时配置并按 AppConfig 结构补默认值。"""
    context = OmegaConf.load(config_source_file())
    schema = OmegaConf.structured(AppConfig)
    return OmegaConf.to_object(OmegaConf.merge(schema, context))


def _copy_into(dst, src) -> None:
    if is_dataclass(dst) and is_dataclass(src):
        for item in fields(dst):
            current = getattr(dst, item.name)
            incoming = getattr(src, item.name)
            if is_dataclass(current) and is_dataclass(incoming):
                _copy_into(current, incoming)
            else:
                setattr(dst, item.name, incoming)


def reload_app_config() -> AppConfig:
    """原地刷新全局 app_config，已持有引用的客户端能读到新值。"""
    _copy_into(app_config, load_app_config())
    return app_config


app_config: AppConfig = load_app_config()
