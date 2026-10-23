#!/usr/bin/env python3
"""Fresh independent format audit (2026-10-23) of the H84-THMS review TIF.

Re-validates ONLY what can be checked from a clean checkout:
 file identity (sha256), portal format/range gate vs data/bridge/sample_submission.tif,
 catalogue overlap vs data/bridge/existing_faults.tif, ZIP contents, note length,
 and an inventory of every other .tif/.zip under docs/downloads (mistaken-submission risk).
It does NOT rerun holdout or the 359-raster uniqueness scan: the feature cache
(.cache/gems_data/processed) is not in a clean checkout. Those numbers remain
2026-10-22 evidence in evidence/h84_exp2_dualseed_holdout.json / h84_uniqueness.json.
"""
import hashlib, json, zipfile
from pathlib import Path
import numpy as np, rasterio
ROOT = Path(__file__).resolve().parents[1]
NAME = "gems84-h84-thms-dink300-37654dots-20261022-2f4190b4-zeros"
NOTE = "H84-THMS silica-valve & 1m/10m scarp-chi Dual-Head Dinkelbach 300m; 37654 dots >3px off cat; HOLDOUT-DTI 0.2255"
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()
out={"audit_date_utc":"2026-10-23","branch":"arena/02ecc790-gemsdoe84","auditor":"fresh_audit_20261023.py (independent of vendor/gems57/validate.py)","submission_name":NAME,"portal_note":NOTE,"portal_note_chars":len(NOTE)}
tif=ROOT/"submissions"/f"{NAME}.tif"
with rasterio.open(tif) as s, rasterio.open(ROOT/"data/bridge/sample_submission.tif") as r, rasterio.open(ROOT/"data/bridge/existing_faults.tif") as c:
    a=s.read(1); ref=r.read(1); cat=c.read(1); foot=np.isfinite(ref)
    out["tif"]={"path":str(tif.relative_to(ROOT)),"sha256":sha(tif),"bytes":tif.stat().st_size,
      "count":s.count,"dtype":s.dtypes[0],"crs":str(s.crs),"shape":[s.height,s.width],
      "transform":[float(x) for x in list(s.transform)[:6]],"nodata":s.nodata,
      "transform_matches_sample":bool(s.transform==r.transform),"crs_matches_sample":bool(s.crs==r.crs)}
    out["values"]={"n_cells":int(a.size),"n_nan":int(np.isnan(a).sum()),"n_inf":int(np.isinf(a).sum()),
      "min":float(a.min()),"max":float(a.max()),"unique":[float(x) for x in np.unique(a)],
      "positive_pixels":int((a==1).sum()),"all_finite":bool(np.isfinite(a).all()),
      "in_range_0_1":bool(a.min()>=0 and a.max()<=1),
      "footprint_cells":int(foot.sum()),"outside_footprint_positive":int((a[~foot]>0).sum()),
      "catalogue_positive_pixels":int((cat>0).sum()),"dots_on_catalogue":int(((a>0)&(cat>0)).sum())}
z=ROOT/"submissions"/f"{NAME}.zip"
with zipfile.ZipFile(z) as zz: out["zip"]={"sha256":sha(z),"bytes":z.stat().st_size,"entries":zz.namelist(),"single_tif":len(zz.namelist())==1 and zz.namelist()[0].endswith(".tif")}
dl=[]
for p in sorted((ROOT/"docs/downloads").glob("*")):
    if p.suffix.lower() in {".tif",".tiff",".zip"}:
        e={"file":p.name,"sha256":sha(p),"is_primary_review_artifact":p.stem==NAME or p.name.startswith(NAME),"submission_authorized":False}
        if p.suffix.lower() in {".tif",".tiff"}:
            try:
                with rasterio.open(p) as s:
                    arr=s.read(1); e.update(n_nan=int(np.isnan(arr).sum()),min=float(np.nanmin(arr)),max=float(np.nanmax(arr)),portal_range_safe=bool(np.isfinite(arr).all() and arr.min()>=0 and arr.max()<=1))
            except Exception as ex: e["error"]=str(ex)
        dl.append(e)
out["docs_downloads_inventory"]=dl
out["format_range_gate_pass"]=bool(out["values"]["all_finite"] and out["values"]["in_range_0_1"] and out["tif"]["count"]==1 and out["tif"]["transform_matches_sample"] and out["values"]["dots_on_catalogue"]==0)
out["not_rerun_this_session"]=["HOLDOUT-DTI (feature cache .cache/gems_data/processed absent in clean checkout; 2026-10-22 value 0.2255, gems57-pooled-hide-v2, 22663 withheld px, 95% CI [0.2101,0.2404] retained as labelled prior evidence, NOT a fresh score)","359-raster uniqueness scan (registry rasters not in clean checkout; 2026-10-22 worst overlap 0.6500 / rho 0.0857 retained as prior evidence)","ORGANIZER-CONFIRMED score for this file (none; no DrivenData submission receipt in repo)"]
out["official_checks_2026_10_23"]={"competition_id":306,"problem_page":"https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/","metric":"alpha=0.2 beta=0.8 R=300m triangular kernel (fetched 2026-10-23)","leaderboard_top_fetched_2026_10_23":{"participant":"xiaofanhu","score":0.4413,"class":"ORGANIZER-CONFIRMED (public leaderboard)"}}
print(json.dumps(out,indent=2))
(ROOT/"evidence/fresh_audit_20261023.json").write_text(json.dumps(out,indent=2)+"\n")
(ROOT/"docs/evidence/fresh_audit_20261023.json").write_text(json.dumps(out,indent=2)+"\n")
