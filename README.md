# Antevorta

Antevorta is a CLI workflow for building a spatial risk surface from geospatial events and factors.

## Methodology

1. Ingest inputs:
- AOI polygon (`aoi.geojson`)
- Event points with timestamp (`events.geojson`)
- Factor layers (for example canopy polygons)

2. Standardize:
- Reproject layers to project CRS
- Clip inputs to AOI
- Persist normalized parquet artifacts

3. Build analysis grid:
- Generate a fixed-size grid over AOI
- Assign stable `grid_id` per cell

4. Engineer features:
- Event counts per grid cell per day
- Rolling event features (`roll_7d_event_count`)
- Spatial factor aggregations (for example `coverage_pct`)

5. Train baseline model:
- Build `target_next_day` label
- Train logistic regression when both classes exist
- Fallback to `dummy_most_frequent` for single-class training windows

6. Predict risk:
- Score each grid cell for next-day risk
- Rank and bucket into risk bands (`top_1pct`, `top_5pct`, `top_20pct`, `low`)

## How To Use

### Setup

```bash
cd /Users/anthonybursae/Documents/GitHub/antevorta
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

### Run full pipeline

```bash
python -m antevorta.cli run --project projects/dc_demo/project.yaml
```

### Run step-by-step (optional)

```bash
python -m antevorta.cli collect aoi --project projects/dc_demo/project.yaml
python -m antevorta.cli collect events --project projects/dc_demo/project.yaml
python -m antevorta.cli collect factors --project projects/dc_demo/project.yaml
python -m antevorta.cli grid build --project projects/dc_demo/project.yaml
python -m antevorta.cli dataset build --project projects/dc_demo/project.yaml
python -m antevorta.cli model train --project projects/dc_demo/project.yaml
python -m antevorta.cli model predict --project projects/dc_demo/project.yaml
```

## Demo Data Walkthrough

Project file: `projects/dc_demo/project.yaml`

- `crs`: `EPSG:3857`
- Grid cell size: `250m`
- Window: `365` days
- Default train/test split: `model.test_days: 2`
- Inputs:
  - `projects/dc_demo/aoi.geojson`
  - `projects/dc_demo/events.geojson`
  - `projects/dc_demo/canopy.geojson`

Expected artifacts after `run`:

- `data/dc_demo/processed/aoi.parquet`
- `data/dc_demo/processed/events.parquet`
- `data/dc_demo/processed/grid.parquet`
- `data/dc_demo/processed/model_table.parquet`
- `data/dc_demo/models/model.pkl`
- `data/dc_demo/reports/metrics.json`
- `data/dc_demo/outputs/risk_surface_YYYY-MM-DD.parquet`

Quick validation:

```bash
ls -la data/dc_demo/processed data/dc_demo/models data/dc_demo/outputs
cat data/dc_demo/reports/metrics.json
```
