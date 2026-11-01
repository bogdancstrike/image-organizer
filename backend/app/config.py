"""Runtime settings, read from environment variables (see docs/configuration.md)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    library_root: Path
    data_dir: Path
    model_dir: Path | None
    openai_api_key: str | None
    openai_model: str
    reasoning_effort: str
    workers: int
    output_dir_name: str
    static_dir: Path | None
    library_name: str = "Library"
    library_host_path: str | None = None  # for display only: where /library lives on the host

    @property
    def ai_available(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def thumbs_dir(self) -> Path:
        return self.data_dir / "thumbs"

    @property
    def journals_dir(self) -> Path:
        return self.data_dir / "journals"


def load_settings() -> Settings:
    env = os.environ
    static = env.get("STATIC_DIR")
    model_dir = env.get("MODEL_DIR")
    return Settings(
        library_root=Path(env.get("LIBRARY_ROOT", "/library")).resolve(),
        data_dir=Path(env.get("DATA_DIR", "/data")),
        model_dir=Path(model_dir) if model_dir else None,
        openai_api_key=(env.get("OPENAI_API_KEY") or "").strip() or None,
        openai_model=env.get("OPENAI_MODEL", "gpt-5.6-luna"),
        reasoning_effort=env.get("OPENAI_REASONING_EFFORT", "low"),
        workers=max(1, int(env.get("WORKERS") or os.cpu_count() or 4)),
        output_dir_name=env.get("OUTPUT_DIR_NAME", "Organized"),
        static_dir=Path(static) if static else None,
        library_name=env.get("LIBRARY_NAME") or "Library",
        library_host_path=env.get("LIBRARY_HOST_PATH") or None,
    )
