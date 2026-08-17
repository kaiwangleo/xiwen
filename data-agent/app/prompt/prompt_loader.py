from pathlib import Path

from omegaconf import OmegaConf

from app.conf.paths import PROMPTS_DIR
DEFAULTS_DIR = PROMPTS_DIR / "defaults"
MANIFEST_PATH = PROMPTS_DIR / "manifest.yaml"

_cache: dict[str, tuple[float, str]] = {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_prompt(name: str) -> str:
    """按 id 读提示词，优先 prompts/ 覆盖，否则用 defaults/；按 mtime 缓存。"""
    path = PROMPTS_DIR / f"{name}.prompt"
    fallback = DEFAULTS_DIR / f"{name}.prompt"
    target = path if path.exists() else fallback
    if not target.exists():
        raise FileNotFoundError(f"prompt not found: {name}")

    mtime = target.stat().st_mtime
    cached = _cache.get(name)
    if cached and cached[0] == mtime:
        return cached[1]

    text = _read_text(target)
    _cache[name] = (mtime, text)
    return text


def invalidate_prompt(name: str | None = None) -> None:
    """丢掉指定或全部提示词缓存，保存后必须调用。"""
    if name is None:
        _cache.clear()
        return
    _cache.pop(name, None)


def load_manifest() -> list[dict]:
    """读取 prompts/manifest.yaml 里的提示词清单。"""
    data = OmegaConf.to_container(OmegaConf.load(MANIFEST_PATH), resolve=True)
    return list(data.get("prompts") or [])


def get_prompt_meta(prompt_id: str) -> dict | None:
    """按 id 取清单元数据，未知 id 返回 None。"""
    for item in load_manifest():
        if item.get("id") == prompt_id:
            return item
    return None


def save_prompt(prompt_id: str, content: str) -> None:
    """覆盖写入 prompts/{file} 并清缓存，下一问生效。"""
    meta = get_prompt_meta(prompt_id)
    if not meta:
        raise KeyError(prompt_id)
    path = PROMPTS_DIR / meta["file"]
    path.write_text(content.replace("\r\n", "\n"), encoding="utf-8")
    invalidate_prompt(prompt_id)


def reset_prompt(prompt_id: str) -> str:
    """用 defaults/ 覆盖当前提示词并返回新内容。"""
    meta = get_prompt_meta(prompt_id)
    if not meta:
        raise KeyError(prompt_id)
    source = DEFAULTS_DIR / meta["file"]
    if not source.exists():
        raise FileNotFoundError(f"default prompt missing: {prompt_id}")
    content = _read_text(source)
    save_prompt(prompt_id, content)
    return content
