from copy import deepcopy
from dataclasses import asdict, is_dataclass

from omegaconf import OmegaConf
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.conf.meta_config import MetaConfig
from app.conf.paths import SEMANTIC_YAML_FALLBACK
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository

YAML_FALLBACK_PATH = SEMANTIC_YAML_FALLBACK

TABLE_ROLES = {"dim", "fact"}
COLUMN_ROLES = {"primary_key", "foreign_key", "dimension", "measure"}

ENSURE_SQL = """
CREATE TABLE IF NOT EXISTS semantic_config (
    id         VARCHAR(32) NOT NULL COMMENT '配置编号',
    config     JSON        NOT NULL COMMENT '语义配置',
    updated_at DATETIME    NOT NULL COMMENT '更新时间',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def _as_dict(obj):
    """dataclass / list 递归转普通 dict，供 YAML 导入使用。"""
    if is_dataclass(obj):
        return {k: _as_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_as_dict(item) for item in obj]
    return obj


def normalize_meta_config(payload: dict | None) -> dict:
    """补齐语义稿缺省字段，不写库。"""
    incoming = deepcopy(payload or {})
    incoming.setdefault("tables", [])
    incoming.setdefault("metrics", [])
    for table in incoming["tables"]:
        table.setdefault("columns", [])
        table.setdefault("description", "")
        table.setdefault("role", "dim")
        for col in table["columns"]:
            col.setdefault("description", "")
            col.setdefault("alias", [])
            col.setdefault("sync", False)
            col.setdefault("role", "dimension")
    for metric in incoming["metrics"]:
        metric.setdefault("description", "")
        metric.setdefault("alias", [])
        metric.setdefault("relevant_columns", [])
    return incoming


def to_meta_config(data: dict) -> MetaConfig:
    """把 dict 转成 MetaConfig，供知识构建六步使用。"""
    schema = OmegaConf.structured(MetaConfig)
    return OmegaConf.to_object(OmegaConf.merge(schema, OmegaConf.create(normalize_meta_config(data))))


def _validate(data: dict) -> list[str]:
    """校验表名/字段名/指标名与 role，返回中文错误列表。"""
    errors: list[str] = []
    tables = data.get("tables") or []
    metrics = data.get("metrics") or []
    names: set[str] = set()
    for idx, table in enumerate(tables, 1):
        name = (table.get("name") or "").strip()
        if not name:
            errors.append(f"第 {idx} 张表缺少表名")
            continue
        if name in names:
            errors.append(f"表名重复: {name}")
        names.add(name)
        role = table.get("role") or ""
        if role not in TABLE_ROLES:
            errors.append(f"表 {name} 的 role 必须是 dim / fact")
        col_names: set[str] = set()
        for col in table.get("columns") or []:
            col_name = (col.get("name") or "").strip()
            if not col_name:
                errors.append(f"表 {name} 有未命名字段")
                continue
            if col_name in col_names:
                errors.append(f"表 {name} 字段重复: {col_name}")
            col_names.add(col_name)
            if (col.get("role") or "") not in COLUMN_ROLES:
                errors.append(f"{name}.{col_name} 的 role 不合法")
    metric_names: set[str] = set()
    for idx, metric in enumerate(metrics, 1):
        name = (metric.get("name") or "").strip()
        if not name:
            errors.append(f"第 {idx} 个指标缺少名称")
            continue
        if name in metric_names:
            errors.append(f"指标名重复: {name}")
        metric_names.add(name)
        for ref in metric.get("relevant_columns") or []:
            if not isinstance(ref, str) or "." not in ref:
                errors.append(f"指标 {name} 的关联字段应为 表.字段: {ref}")
        if not (metric.get("relevant_columns") or []):
            errors.append(f"指标 {name} 至少要关联一个数仓字段")
    return errors


def _validate_against_schema(data: dict, schema: list[dict]) -> list[str]:
    """对照数仓 information_schema，拒绝不存在的表/字段。"""
    allowed = {item["name"]: {col["name"] for col in item.get("columns") or []} for item in schema}
    errors: list[str] = []
    for table in data.get("tables") or []:
        name = (table.get("name") or "").strip()
        if not name:
            continue
        if name not in allowed:
            errors.append(f"表 {name} 不在当前数据源中")
            continue
        for col in table.get("columns") or []:
            col_name = (col.get("name") or "").strip()
            if col_name and col_name not in allowed[name]:
                errors.append(f"{name}.{col_name} 不在数据源表中")
    known_cols = {f"{table}.{col}" for table, cols in allowed.items() for col in cols}
    for metric in data.get("metrics") or []:
        name = (metric.get("name") or "").strip() or "未命名指标"
        for ref in metric.get("relevant_columns") or []:
            if ref not in known_cols:
                errors.append(f"指标 {name} 关联了不存在的字段: {ref}")
    return errors


def _load_yaml_fallback() -> dict | None:
    """空库时从 conf/meta_config.yaml 读一份种子稿。"""
    if not YAML_FALLBACK_PATH.exists():
        return None
    context = OmegaConf.load(YAML_FALLBACK_PATH)
    schema = OmegaConf.structured(MetaConfig)
    return _as_dict(OmegaConf.to_object(OmegaConf.merge(schema, context)))


async def ensure_semantic_table(engine: AsyncEngine) -> None:
    """启动时确保元库存在 semantic_config 表。"""
    async with engine.begin() as conn:
        await conn.execute(text(ENSURE_SQL))


async def load_meta_config(session: AsyncSession, *, seed: bool = True) -> dict:
    """读语义稿；库空且 seed 时用 yaml 写入后再返回。"""
    repo = MetaMySQLRepository(session)
    data = await repo.get_semantic_config()
    if data is None and seed:
        data = _load_yaml_fallback()
        if data is not None:
            data = normalize_meta_config(data)
            await repo.save_semantic_config(data)
            await session.commit()
    return normalize_meta_config(data)


async def save_meta_config(session: AsyncSession, payload: dict, schema: list[dict] | None = None) -> dict:
    """校验并写入 semantic_config，不触发知识构建。"""
    incoming = normalize_meta_config(payload)
    errors = _validate(incoming)
    if schema is not None:
        errors.extend(_validate_against_schema(incoming, schema))
    if errors:
        raise ValueError("；".join(errors))
    repo = MetaMySQLRepository(session)
    await repo.save_semantic_config(incoming)
    await session.commit()
    return {"config": await load_meta_config(session, seed=False), "rebuild_required": True}
