from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    project_dir_name: str = ".antevorta"
    seed: int = 42
    background_multiplier: int = 3

    @property
    def project_dir(self) -> Path:
        return Path.cwd() / self.project_dir_name


CONFIG = AppConfig()
