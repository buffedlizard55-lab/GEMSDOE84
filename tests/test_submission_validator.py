import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from scripts.validate_submission import audit
    HAS_GEO = True
except ImportError:
    HAS_GEO = False


@unittest.skipUnless(HAS_GEO, "install requirements-validation.txt")
class SubmissionValidatorTests(unittest.TestCase):
    def _write(self, path: Path, values, *, dtype="float32", nodata=None, transform=None):
        array = np.asarray(values, dtype=dtype)
        if array.ndim == 2:
            array = array[np.newaxis, ...]
        profile = {
            "driver": "GTiff", "height": array.shape[1], "width": array.shape[2],
            "count": array.shape[0], "dtype": dtype, "crs": "EPSG:32611",
            "transform": transform or from_origin(500000, 4500000, 100, 100),
        }
        if nodata is not None:
            profile["nodata"] = nodata
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(array)

    def test_valid_single_band_matches_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref, candidate = root / "ref.tif", root / "candidate.tif"
            self._write(ref, np.zeros((4, 5), dtype="float32"))
            self._write(candidate, np.full((4, 5), 0.25, dtype="float32"))
            result = audit(candidate, ref)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["checks"]["footprint_has_no_nan"])
        self.assertTrue(result["checks"]["all_finite_values_in_[0,1]"])
        self.assertTrue(result["checks"]["crs_match"])
        self.assertTrue(result["checks"]["shape_match"])
        self.assertTrue(result["checks"]["transform_match"])
        self.assertEqual(len(result["sha256"]), 64)

    def test_rejects_out_of_range_values_and_interior_nan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref, candidate = root / "ref.tif", root / "candidate.tif"
            self._write(ref, np.zeros((3, 3), dtype="float32"))
            values = np.zeros((3, 3), dtype="float32")
            values[0, 0] = 1.2
            values[1, 1] = np.nan
            self._write(candidate, values, nodata=np.nan)
            result = audit(candidate, ref)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["checks"]["nan_inside_footprint"], 1)
        self.assertEqual(result["checks"]["finite_values_outside_[0,1]_count"], 1)

    def test_rejects_wrong_transform(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref, candidate = root / "ref.tif", root / "candidate.tif"
            self._write(ref, np.zeros((2, 2), dtype="float32"))
            self._write(candidate, np.zeros((2, 2), dtype="float32"),
                        transform=from_origin(500100, 4500000, 100, 100))
            result = audit(candidate, ref)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["checks"]["transform_match"])


if __name__ == "__main__":
    unittest.main()
