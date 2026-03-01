# Antevorta

Antevorta is a deterministic CLI for geospatial predictive assessment.

## Setup

```bash
cd /Users/anthonybursae/Documents/GitHub/antevorta
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Supported CLI Commands

```bash
antevorta init --aoi aoi.geojson
antevorta add-events events.csv
antevorta add-events events.geojson --time-field event_time
antevorta add-factor factor.geojson --type distance
antevorta build-grid --resolution 500
antevorta assess
antevorta validate --kfold 5
```

## dc_demo Quickstart

```bash
cd /Users/anthonybursae/Documents/GitHub/antevorta
source .venv/bin/activate

python -m antevorta.cli init --aoi projects/dc_demo/aoi.geojson
python -m antevorta.cli add-events projects/dc_demo/events.geojson --time-field event_time
python -m antevorta.cli add-factor projects/dc_demo/canopy.geojson --type distance
python -m antevorta.cli build-grid --resolution 100
python -m antevorta.cli assess
python -m antevorta.cli validate --kfold 3
```

## Inputs

- AOI: GeoJSON polygon
- Events:
  - CSV with `id`, `latitude`, `longitude`, `timestamp`
  - or GeoJSON points with a timestamp property (for example `event_time`)
- Factors:
  - Vector: GeoJSON or Shapefile
  - Raster: GeoTIFF (`.tif`, `.tiff`)

## Outputs

Project state is stored under `./.antevorta/`.

- `./.antevorta/project.json`
- `./.antevorta/data/events.csv`
- `./.antevorta/data/grid.geojson`
- `./.antevorta/factors/*`

Assessment exports are written to the current working directory:

- `likelihood_grid.geojson`
- `ranked_grid.csv`
- `factor_weights.csv`
