from copy import deepcopy
from dataclasses import asdict
from typing import Any

from omegaconf import OmegaConf

from app.conf.app_config import (
    app_config,
    config_file,
    config_source_file,
    reload_app_config,
)


SECRET_KEYS = {"password", "api_key"}

KNOWLEDGE_STEP_ORDER = [
    "load_config",
    "save_tables",
    "index_columns",
    "index_values",
    "save_metrics",
    "index_metrics",
]


def _mask_value(key: str, value: Any) -> Any:
    """密钥只露后四位，空值原样返回。"""
    if key in SECRET_KEYS and value:
        text = str(value)
        return "****" + text[-4:] if len(text) > 4 else "****"
    return value


def _mask_tree(obj: Any, key: str | None = None) -> Any:
    """递归打码配置树里的 password / api_key。"""
    if isinstance(obj, dict):
        return {k: _mask_tree(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_mask_tree(item) for item in obj]
    return _mask_value(key or "", obj)


def _is_masked(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("****")


def _restore_secrets(incoming: Any, original: Any, key: str | None = None) -> Any:
    """前端回传 **** 时还原成当前明文，避免把打码写进 yaml。"""
    if _is_masked(incoming) and key in SECRET_KEYS:
        return original
    if isinstance(incoming, dict) and isinstance(original, dict):
        merged = {}
        for k, v in incoming.items():
            merged[k] = _restore_secrets(v, original.get(k), k)
        return merged
    if isinstance(incoming, list):
        return incoming
    return incoming


def config_as_dict(mask: bool = True) -> dict:
    """导出当前运行时配置，默认打码密钥。"""
    data = asdict(app_config)
    return _mask_tree(data) if mask else data


def knowledge_warnings(payload: dict | None = None) -> list[str]:
    """检查 6 步开关组合是否会导致后续步骤读不到数据。"""
    source = payload or asdict(app_config)
    steps = (source.get("knowledge_build") or {}).get("steps") or {}
    warnings: list[str] = []

    def enabled(step_id: str) -> bool:
        return bool((steps.get(step_id) or {}).get("enabled", True))

    if not enabled("load_config") and any(
        enabled(step) for step in KNOWLEDGE_STEP_ORDER if step != "load_config"
    ):
        warnings.append("关闭 load_config 后其余步骤读不到语义配置，构建会跳过后续步骤")
    if not enabled("save_tables") and (enabled("index_columns") or enabled("index_values")):
        warnings.append("关闭 save_tables 却开启 index_columns / index_values：本轮没有字段数据")
    if not enabled("save_metrics") and enabled("index_metrics"):
        warnings.append("关闭 save_metrics 却开启 index_metrics：本轮没有指标数据")
    return warnings


def save_config(payload: dict) -> dict:
    """合并写入 app_config.yaml 并热加载；返回 previous/applied 供连接器 reload。"""
    original = asdict(app_config)
    incoming = _restore_secrets(deepcopy(payload), original)
    current_file = OmegaConf.load(config_source_file())
    merged = OmegaConf.merge(current_file, OmegaConf.create(incoming))
    OmegaConf.save(merged, config_file)
    reload_app_config()
    applied = asdict(app_config)
    return {
        "config": _mask_tree(applied),
        "restart_required": False,
        "warnings": knowledge_warnings(applied),
        "previous": original,
        "applied": applied,
    }
