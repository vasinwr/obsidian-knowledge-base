"""Configuration management — TOML config file + environment variables."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "kb"
DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "kb"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"

DEFAULTS = {
    "vault_path": "",
    "vault_subfolder": "Knowledge Base",
    "llm_provider": "claude",
    "llm_model": "claude-sonnet-4-20250514",
    "embedding_model": "all-MiniLM-L6-v2",
    "chunk_size": 512,
    "chunk_overlap": 64,
}


@dataclass
class Config:
    vault_path: str = ""
    vault_subfolder: str = "Knowledge Base"
    llm_provider: str = "claude"
    llm_model: str = "claude-sonnet-4-20250514"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 64
    data_dir: Path = field(default_factory=lambda: DEFAULT_DATA_DIR)

    # API keys resolved from environment
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    twitter_bearer_token: str = ""

    @property
    def vault(self) -> Path:
        return Path(self.vault_path)

    @property
    def vault_kb_dir(self) -> Path:
        return self.vault / self.vault_subfolder

    @property
    def vault_attachments_dir(self) -> Path:
        return self.vault / "attachments"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "kb.db"

    @property
    def external_plugins_dir(self) -> Path:
        return Path.cwd() / "plugins"


def load_config(path: Path | None = None) -> Config:
    """Load configuration from TOML file and overlay environment variables."""
    config_path = path or DEFAULT_CONFIG_PATH
    values: dict = dict(DEFAULTS)

    if config_path.exists():
        with open(config_path, "rb") as f:
            toml_data = tomllib.load(f)
        values.update(toml_data)

    cfg = Config(
        vault_path=values["vault_path"],
        vault_subfolder=values["vault_subfolder"],
        llm_provider=values["llm_provider"],
        llm_model=values["llm_model"],
        embedding_model=values["embedding_model"],
        chunk_size=int(values["chunk_size"]),
        chunk_overlap=int(values["chunk_overlap"]),
    )

    # Resolve API keys from environment
    cfg.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    cfg.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    cfg.twitter_bearer_token = os.environ.get("TWITTER_BEARER_TOKEN", "")

    return cfg


def save_config(cfg: Config, path: Path | None = None) -> None:
    """Persist configuration to a TOML file."""
    config_path = path or DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f'vault_path = "{cfg.vault_path}"',
        f'vault_subfolder = "{cfg.vault_subfolder}"',
        f'llm_provider = "{cfg.llm_provider}"',
        f'llm_model = "{cfg.llm_model}"',
        f'embedding_model = "{cfg.embedding_model}"',
        f"chunk_size = {cfg.chunk_size}",
        f"chunk_overlap = {cfg.chunk_overlap}",
    ]
    config_path.write_text("\n".join(lines) + "\n")


def ensure_dirs(cfg: Config) -> None:
    """Create all required directories if they don't exist."""
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.chroma_dir.mkdir(parents=True, exist_ok=True)
    cfg.vault_kb_dir.mkdir(parents=True, exist_ok=True)
    cfg.vault_attachments_dir.mkdir(parents=True, exist_ok=True)
