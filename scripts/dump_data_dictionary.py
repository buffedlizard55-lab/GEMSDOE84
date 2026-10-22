#!/usr/bin/env python3
"""Dump the exact band descriptions/metadata from the restored GeoTIFFs into
registry/data_dictionary.json, so the band dictionary used throughout this repo is read
verbatim from the file's own metadata rather than retyped from the competition page by hand."""
from pathlib import Path
import json
import rasterio
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = {}
    for name in ["training_features.tif", "labels.tif", "sample_submission.tif"]:
        path = ROOT / "data" / name
        with rasterio.open(path) as ds:
            info = {
                "count": ds.count,
                "dtype": ds.dtypes[0],
                "shape": list(ds.shape),
                "crs": str(ds.crs),
                "transform": list(ds.transform)[:6],
                "bounds": list(ds.bounds),
                "nodata": ds.nodata,
                "descriptions": list(ds.descriptions),
            }
            out[name] = info
    (ROOT / "registry" / "data_dictionary.json").write_text(json.dumps(out, indent=2) + "\n")
    print("wrote registry/data_dictionary.json")


if __name__ == "__main__":
    main()
