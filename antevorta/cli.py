from __future__ import annotations

import argparse
import logging
from pathlib import Path

from antevorta.events import add_events, load_events_geodataframe
from antevorta.export import export_assessment
from antevorta.factors import add_factor, load_factors
from antevorta.grid import build_grid, load_grid
from antevorta.model import build_training_data, factor_weights, predict_likelihood, train_logistic_regression
from antevorta.project import ProjectState, initialize_project, load_manifest
from antevorta.validation import validate_model


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _require_file(path: str) -> Path:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    return file_path


def cmd_init(args: argparse.Namespace) -> None:
    aoi = _require_file(args.aoi)
    if aoi.suffix.lower() != ".geojson":
        raise ValueError("AOI must be a GeoJSON file")
    initialize_project(aoi.resolve())
    logging.info("Initialized project with AOI: %s", aoi)


def cmd_add_events(args: argparse.Namespace) -> None:
    state = ProjectState.from_cwd()
    stored = add_events(
        state,
        _require_file(args.events).resolve(),
        time_field=str(args.time_field),
    )
    logging.info("Stored events: %s", stored)


def cmd_add_factor(args: argparse.Namespace) -> None:
    state = ProjectState.from_cwd()
    factor = add_factor(state, _require_file(args.factor).resolve(), args.type)
    logging.info("Registered factor: %s (%s)", factor["name"], factor["source"])


def cmd_build_grid(args: argparse.Namespace) -> None:
    state = ProjectState.from_cwd()
    path = build_grid(state, float(args.resolution))
    logging.info("Built grid: %s", path)


def _prepare_assessment_inputs(state: ProjectState):
    manifest = load_manifest(state)
    events_path = manifest.get("events_path")
    if not isinstance(events_path, str):
        raise ValueError("Events missing. Run: antevorta add-events <events-file>")

    events = load_events_geodataframe(Path(events_path))
    grid = load_grid(state)
    factors = load_factors(state)
    return events, grid, factors


def cmd_assess(_: argparse.Namespace) -> None:
    state = ProjectState.from_cwd()
    events, grid, factors = _prepare_assessment_inputs(state)

    data = build_training_data(events, grid, factors)
    fitted = train_logistic_regression(data)
    ranked = predict_likelihood(fitted, grid, factors)
    weights = factor_weights(fitted)

    outputs = export_assessment(grid, ranked, weights, Path.cwd())
    logging.info("Wrote likelihood surface: %s", outputs["likelihood_grid"])
    logging.info("Wrote ranked grid: %s", outputs["ranked_grid"])
    logging.info("Wrote factor weights: %s", outputs["factor_weights"])


def cmd_validate(args: argparse.Namespace) -> None:
    state = ProjectState.from_cwd()
    events, grid, factors = _prepare_assessment_inputs(state)
    data = build_training_data(events, grid, factors)
    metrics = validate_model(data, int(args.kfold))
    logging.info(
        "Cross-validation complete: k=%d auc_mean=%.6f auc_std=%.6f",
        int(metrics["kfold"]),
        metrics["auc_mean"],
        metrics["auc_std"],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="antevorta")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--aoi", required=True)
    p_init.set_defaults(func=cmd_init)

    p_events = sub.add_parser("add-events")
    p_events.add_argument("events")
    p_events.add_argument("--time-field", default="timestamp")
    p_events.set_defaults(func=cmd_add_events)

    p_factor = sub.add_parser("add-factor")
    p_factor.add_argument("factor")
    p_factor.add_argument("--type", required=True, choices=["distance"])
    p_factor.set_defaults(func=cmd_add_factor)

    p_grid = sub.add_parser("build-grid")
    p_grid.add_argument("--resolution", required=True, type=float)
    p_grid.set_defaults(func=cmd_build_grid)

    p_assess = sub.add_parser("assess")
    p_assess.set_defaults(func=cmd_assess)

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--kfold", required=True, type=int)
    p_validate.set_defaults(func=cmd_validate)

    return parser


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
