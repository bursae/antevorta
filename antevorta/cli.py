from __future__ import annotations

import argparse
from pathlib import Path


def _load_cfg(project_yaml: str) -> dict:
    from antevorta.core.config import load_project_config
    from antevorta.core.storage import ProjectPaths, ensure_project_dirs

    cfg = load_project_config(project_yaml)
    ensure_project_dirs(ProjectPaths(cfg["name"]))
    return cfg


def cmd_project_init(args: argparse.Namespace) -> None:
    from antevorta.core.storage import ProjectPaths, ensure_project_dirs

    name = args.name
    project_dir = Path("projects") / name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "sources").mkdir(parents=True, exist_ok=True)

    template_path = Path(__file__).parent / "templates" / "project.yaml"
    template = template_path.read_text(encoding="utf-8")
    template = template.replace("{{PROJECT_NAME}}", name)
    (project_dir / "project.yaml").write_text(template, encoding="utf-8")

    ensure_project_dirs(ProjectPaths(name))
    print(f"Initialized project at {project_dir / 'project.yaml'}")


def cmd_collect_aoi(args: argparse.Namespace) -> None:
    from antevorta.ingest.aoi import collect_aoi

    cfg = _load_cfg(args.project)
    collect_aoi(cfg)
    print("Wrote data/<project>/processed/aoi.parquet")


def cmd_collect_events(args: argparse.Namespace) -> None:
    from antevorta.ingest.events import collect_events

    cfg = _load_cfg(args.project)
    collect_events(cfg)
    print("Wrote data/<project>/processed/events.parquet")


def cmd_collect_factors(args: argparse.Namespace) -> None:
    from antevorta.ingest.factors import collect_factors

    cfg = _load_cfg(args.project)
    collect_factors(cfg)
    print("Wrote data/<project>/processed/factors/*.parquet")


def cmd_grid_build(args: argparse.Namespace) -> None:
    import geopandas as gpd
    from antevorta.core.grid import build_grid
    from antevorta.core.storage import ProjectPaths

    cfg = _load_cfg(args.project)
    paths = ProjectPaths(cfg["name"])

    aoi = gpd.read_parquet(paths.processed / "aoi.parquet")
    grid = build_grid(aoi, float(cfg["grid"]["cell_size_m"]), cfg["name"])
    grid.to_parquet(paths.processed / "grid.parquet")
    print("Wrote data/<project>/processed/grid.parquet")


def cmd_dataset_build(args: argparse.Namespace) -> None:
    from antevorta.features.dataset import build_dataset

    cfg = _load_cfg(args.project)
    build_dataset(cfg)
    print("Wrote data/<project>/processed/model_table.parquet")


def cmd_model_train(args: argparse.Namespace) -> None:
    from antevorta.model.baseline import train_baseline

    cfg = _load_cfg(args.project)
    train_baseline(cfg, test_days=args.test_days)
    print("Wrote data/<project>/models/model.pkl and reports/metrics.json")


def cmd_model_predict(args: argparse.Namespace) -> None:
    from antevorta.model.baseline import predict_risk

    cfg = _load_cfg(args.project)
    out = predict_risk(cfg, as_of_date=args.date)
    forecast_date = out["forecast_date"].iloc[0].date()
    print(f"Wrote data/<project>/outputs/risk_surface_{forecast_date}.parquet")


def cmd_run(args: argparse.Namespace) -> None:
    import geopandas as gpd
    from antevorta.core.grid import build_grid
    from antevorta.core.storage import ProjectPaths
    from antevorta.features.dataset import build_dataset
    from antevorta.ingest.aoi import collect_aoi
    from antevorta.ingest.events import collect_events
    from antevorta.ingest.factors import collect_factors
    from antevorta.model.baseline import predict_risk, train_baseline

    cfg = _load_cfg(args.project)

    collect_aoi(cfg)
    collect_events(cfg)
    collect_factors(cfg)

    paths = ProjectPaths(cfg["name"])
    aoi = gpd.read_parquet(paths.processed / "aoi.parquet")
    grid = build_grid(aoi, float(cfg["grid"]["cell_size_m"]), cfg["name"])
    grid.to_parquet(paths.processed / "grid.parquet")

    build_dataset(cfg)
    train_baseline(cfg, test_days=args.test_days)
    predict_risk(cfg, as_of_date=args.date)
    print("Run complete.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="antevorta")
    sub = parser.add_subparsers(dest="command", required=True)

    p_project = sub.add_parser("project")
    p_project_sub = p_project.add_subparsers(dest="project_cmd", required=True)
    p_init = p_project_sub.add_parser("init")
    p_init.add_argument("--name", required=True)
    p_init.set_defaults(func=cmd_project_init)

    p_collect = sub.add_parser("collect")
    p_collect_sub = p_collect.add_subparsers(dest="collect_cmd", required=True)
    for name, func in [
        ("aoi", cmd_collect_aoi),
        ("events", cmd_collect_events),
        ("factors", cmd_collect_factors),
    ]:
        p = p_collect_sub.add_parser(name)
        p.add_argument("--project", required=True)
        p.set_defaults(func=func)

    p_grid = sub.add_parser("grid")
    p_grid_sub = p_grid.add_subparsers(dest="grid_cmd", required=True)
    p_grid_build = p_grid_sub.add_parser("build")
    p_grid_build.add_argument("--project", required=True)
    p_grid_build.set_defaults(func=cmd_grid_build)

    p_dataset = sub.add_parser("dataset")
    p_dataset_sub = p_dataset.add_subparsers(dest="dataset_cmd", required=True)
    p_dataset_build = p_dataset_sub.add_parser("build")
    p_dataset_build.add_argument("--project", required=True)
    p_dataset_build.set_defaults(func=cmd_dataset_build)

    p_model = sub.add_parser("model")
    p_model_sub = p_model.add_subparsers(dest="model_cmd", required=True)

    p_train = p_model_sub.add_parser("train")
    p_train.add_argument("--project", required=True)
    p_train.add_argument("--test-days", type=int, default=30)
    p_train.set_defaults(func=cmd_model_train)

    p_predict = p_model_sub.add_parser("predict")
    p_predict.add_argument("--project", required=True)
    p_predict.add_argument("--date")
    p_predict.set_defaults(func=cmd_model_predict)

    p_run = sub.add_parser("run")
    p_run.add_argument("--project", required=True)
    p_run.add_argument("--test-days", type=int, default=30)
    p_run.add_argument("--date")
    p_run.set_defaults(func=cmd_run)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
