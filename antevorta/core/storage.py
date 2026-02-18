from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    project_name: str

    @property
    def root(self) -> Path:
        return Path("data") / self.project_name

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def processed(self) -> Path:
        return self.root / "processed"

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def metadata(self) -> Path:
        return self.root / "metadata"

    @property
    def factors_dir(self) -> Path:
        return self.processed / "factors"


def ensure_project_dirs(paths: ProjectPaths) -> None:
    for p in [
        paths.root,
        paths.raw,
        paths.processed,
        paths.outputs,
        paths.models,
        paths.reports,
        paths.metadata,
        paths.factors_dir,
    ]:
        p.mkdir(parents=True, exist_ok=True)
