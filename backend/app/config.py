"""环境配置（Cursor Cloud Agents 等）。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 始终从 backend/.env 加载（与 uvicorn 启动时当前工作目录无关）
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """见 Cursor Cloud Agents 文档：需 Dashboard 申请的 API Key；仓库格式 owner/repo。"""

    cursor_api_key: str | None = None
    cursor_api_base: str = "https://api.cursor.com"
    """API 根 URL，不含尾路径。"""
    cursor_repository: str | None = None
    """GitHub 仓库 full name，例如 org/repo。未配置时仅模拟调用。"""
    cursor_branch: str = "main"
    cursor_webhook_secret: str | None = None
    """若设置，则请求头 X-Studio-Webhook-Secret 须与其一致（简易共享密钥）。"""

    studio_output_preview_url: str = "http://127.0.0.1:5180"
    """本地小游戏产出预览（Vite dev server）浏览器地址，供办公室 iframe。"""
    studio_output_dir: str = "../output/mini-game"
    """相对 `backend` 工作目录的产出项目路径；须与推送到 CURSOR_REPOSITORY 的目录一致，Agent 才能改到代码。"""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


def resolved_studio_output_dir(settings: Settings) -> Path:
    """解析产出目录绝对路径（uvicorn 一般在 backend/ 下启动）。"""
    p = Path(settings.studio_output_dir)
    if p.is_absolute():
        return p.resolve()
    return (Path.cwd() / p).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """热重载或测试时如需重新读 .env 可调用（一般无需使用）。"""
    get_settings.cache_clear()
