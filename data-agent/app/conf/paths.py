"""项目根路径与配置文件位置，避免各处手写 parents[2]。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_CONFIG_PATH = ROOT / "conf" / "app_config.yaml"
APP_CONFIG_EXAMPLE_PATH = ROOT / "conf" / "app_config.example.yaml"
SEMANTIC_YAML_FALLBACK = ROOT / "conf" / "meta_config.yaml"
PROMPTS_DIR = ROOT / "prompts"
