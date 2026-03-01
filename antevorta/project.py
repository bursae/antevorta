from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from antevorta.config import CONFIG
from antevorta.io import ensure_dir, read_json, write_json


@dataclass
class ProjectState:
    root: Path
    data_dir: Path
    factors_dir: Path
    manifest_path: Path

    @classmethod
    def from_cwd(cls) -> "ProjectState":
        root = CONFIG.project_dir
        return cls(
            root=root,
            data_dir=root / "data",
            factors_dir=root / "factors",
            manifest_path=root / "project.json",
        )

    def require_initialized(self) -> None:
        if not self.manifest_path.exists():
            raise FileNotFoundError(
                "Project not initialized. Run: antevorta init --aoi <aoi.geojson>"
            )


def initialize_project(aoi_path: Path) -> ProjectState:
    state = ProjectState.from_cwd()
    ensure_dir(state.root)
    ensure_dir(state.data_dir)
    ensure_dir(state.factors_dir)

    manifest = {
        "aoi_path": str(aoi_path.resolve()),
        "events_path": None,
        "grid_path": None,
        "factors": [],
    }
    write_json(state.manifest_path, manifest)
    return state


def load_manifest(state: ProjectState) -> dict[str, object]:
    state.require_initialized()
    return read_json(state.manifest_path)


def save_manifest(state: ProjectState, manifest: dict[str, object]) -> None:
    write_json(state.manifest_path, manifest)
