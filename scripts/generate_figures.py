#!/usr/bin/env python3
"""Generate 4-panel diagnostic figure for Lane H84-THMS (GEMSDOE84)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import grid as GRID  # noqa: E402


def main() -> int:
    card = json.loads((ROOT / "run_card.json").read_text())
    canary = json.loads((ROOT / "evidence" / "h84_exp1_canary.json").read_text())
    exp2 = json.loads((ROOT / "evidence" / "h84_exp2_dualseed_holdout.json").read_text())

    g = GRID.load_grid(ROOT / "data" / "bridge")
    foot = g.footprint
    cat = g.catalogue

    surf_path = ROOT / ".cache" / "gems_data" / "processed" / "h84_surf_full_loqo.f16.npy"
    surf = np.load(surf_path).astype(np.float32)

    with rasterio.open(ROOT / card["submissions_tif"]) as ds:
        dots = ds.read(1) > 0.5

    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)

    fig, axes = plt.subplots(2, 2, figsize=(15, 11.5), dpi=130)
    fig.patch.set_facecolor("#0f172a")
    for ax in axes.ravel():
        ax.set_facecolor("#1e293b")
        for spine in ax.spines.values():
            spine.set_color("#475569")
        ax.tick_params(colors="#cbd5e1", labelsize=9)

    # Panel A: Full-catalogue 4-quadrant LOQO probability surface (downsampled 4x for crisp rendering)
    ax0 = axes[0, 0]
    disp = np.where(foot[::4, ::4], surf[::4, ::4], np.nan)
    im0 = ax0.imshow(disp, cmap="magma", vmin=0.0, vmax=0.72, interpolation="nearest")
    cy, cx = np.nonzero(cat[::4, ::4])
    ax0.scatter(cx, cy, s=0.12, c="#38bdf8", alpha=0.35, label="Mapped Catalogue (60,988 px)")
    ax0.set_title(
        "A. H84-THMS 96-Channel 4-Quadrant LOQO Surface + Mapped Catalogue",
        color="#f8fafc",
        fontsize=11,
        fontweight="bold",
    )
    ax0.set_xlabel("Column (4x decimated, EPSG:32611)", color="#cbd5e1", fontsize=9)
    ax0.set_ylabel("Row (4x decimated)", color="#cbd5e1", fontsize=9)
    cb0 = fig.colorbar(im0, ax=ax0, fraction=0.042, pad=0.03)
    cb0.ax.yaxis.set_tick_params(color="#cbd5e1")
    plt.setp(plt.getp(cb0.ax.axes, "yticklabels"), color="#cbd5e1", fontsize=8)
    cb0.set_label("Out-of-Quadrant Probability p_LOQO", color="#cbd5e1", fontsize=9)

    # Panel B: 37,654 Emitted Binary Dots Colored by Off-Catalogue Distance Regime
    ax1 = axes[0, 1]
    bg = np.where(foot[::4, ::4], 0.12, np.nan)
    ax1.imshow(bg, cmap="Greys", vmin=0.0, vmax=1.0, extent=[0, foot.shape[1], foot.shape[0], 0])
    dy, dx = np.nonzero(dots)
    dd = d_cat[dy, dx]
    m_near = (dd > 3.0) & (dd <= 12.0)
    m_mid = (dd > 12.0) & (dd <= 50.0)
    m_far = dd > 50.0
    ax1.scatter(
        dx[m_near],
        dy[m_near],
        s=0.30,
        c="#22c55e",
        alpha=0.65,
        label=f"300m–1.2km Continuation/Splay ({int(m_near.sum()):,})",
    )
    ax1.scatter(
        dx[m_mid],
        dy[m_mid],
        s=0.35,
        c="#f59e0b",
        alpha=0.75,
        label=f"1.2km–5.0km Relay/Piedmont ({int(m_mid.sum()):,})",
    )
    if m_far.any():
        ax1.scatter(
            dx[m_far],
            dy[m_far],
            s=1.2,
            c="#f43f5e",
            alpha=0.95,
            label=f">5.0km Blind Intrabasin ({int(m_far.sum()):,})",
        )
    ax1.set_title(
        "B. 37,654 Emitted Binary Dots (d > 3.0 px Off Catalogue, Overlap <= 0.650)",
        color="#f8fafc",
        fontsize=11,
        fontweight="bold",
    )
    ax1.set_xlabel("Column (px, 100 m grid)", color="#cbd5e1", fontsize=9)
    ax1.set_ylabel("Row (px, 100 m grid)", color="#cbd5e1", fontsize=9)
    leg1 = ax1.legend(loc="lower left", fontsize=8, facecolor="#0f172a", edgecolor="#475569", markerscale=6)
    for text in leg1.get_texts():
        text.set_color("#f8fafc")

    # Panel C: Paired 6-Arm Dual-Seed HOLDOUT-DTI Progression (22,663 withheld positives)
    ax2 = axes[1, 0]
    arms = [
        ("A0_random", "A0: Random\nControl"),
        ("A1_phys72_poisson", "A1: 72-Ch\nPhys+THM"),
        ("A2_struct24_poisson", "A2: 24-Ch\nStruct+Coup"),
        ("A3_thms96_poisson", "A3: 96-Ch\nPoisson (d>2)"),
        ("A4_thms96_dink_c20", "A4: 96-Ch Dink\nUncapped (d>2)"),
        ("A5_thms96_dualhead_dink_c30", "A5: 96-Ch Dual-Head\nDink (d>3, Cap)"),
    ]
    scores_pool = exp2["dualseed_pooled_summary"]["scores"]
    scores_s30 = exp2["seeds"]["30"]["summary"]["scores"]
    scores_s20 = exp2["seeds"]["20"]["summary"]["scores"]

    x = np.arange(len(arms))
    w = 0.26
    vals_pool = [scores_pool[k]["dti"] for k, _ in arms]
    err_lo = [scores_pool[k]["dti"] - scores_pool[k]["ci95"][0] for k, _ in arms]
    err_hi = [scores_pool[k]["ci95"][1] - scores_pool[k]["dti"] for k, _ in arms]
    vals_30 = [scores_s30[k]["dti"] for k, _ in arms]
    vals_20 = [scores_s20[k]["dti"] for k, _ in arms]

    ax2.bar(x - w, vals_30, width=w, color="#38bdf8", alpha=0.85, label="Seed 30 (11,342 px)")
    ax2.bar(
        x,
        vals_pool,
        width=w,
        yerr=[err_lo, err_hi],
        capsize=3,
        color="#22c55e",
        ecolor="#f8fafc",
        label="Dual-Seed Pooled (22,663 px, 95% CI)",
    )
    ax2.bar(x + w, vals_20, width=w, color="#a855f7", alpha=0.85, label="Seed 20 (11,321 px)")
    ax2.axhline(0.206817, color="#f59e0b", linestyle="--", linewidth=1.2, label="GEMSDOE83 H83-GVCD (0.2068)")
    ax2.axhline(0.165778, color="#94a3b8", linestyle=":", linewidth=1.2, label="GEMSDOE82 H82-CSAM (0.1658)")
    for idx_b, v in enumerate(vals_pool):
        ax2.text(idx_b, v + 0.015, f"{v:.4f}", ha="center", va="bottom", color="#f8fafc", fontsize=8, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels([lbl for _, lbl in arms], fontsize=8, color="#e2e8f0")
    ax2.set_ylim(0.0, 0.275)
    ax2.set_ylabel("HOLDOUT-DTI (gems57-pooled-hide-v2)", color="#cbd5e1", fontsize=9)
    ax2.set_title(
        "C. Paired 6-Arm Dual-Seed HOLDOUT-DTI Progression (22,663 Withheld Pixels)",
        color="#f8fafc",
        fontsize=11,
        fontweight="bold",
    )
    leg2 = ax2.legend(loc="upper left", fontsize=8, facecolor="#0f172a", edgecolor="#475569")
    for text in leg2.get_texts():
        text.set_color("#f8fafc")

    # Panel D: Top 12 Single-Feature Leakage Canary Symmetric AUCs vs 0.90 Gate
    ax3 = axes[1, 1]
    top_feats = canary["seeds"]["30"]["top_15_features"][:12][::-1]
    s20_map = canary["seeds"]["20"]["per_feature_symmetric_auc"]
    f_names = [item["feature"] for item in top_feats]
    v30 = [item["symmetric_auc"] for item in top_feats]
    v20 = [s20_map.get(nm, 0.5) for nm in f_names]
    yh = np.arange(len(f_names))
    ax3.barh(yh - 0.18, v30, height=0.35, color="#38bdf8", label="Seed 30 AUC")
    ax3.barh(yh + 0.18, v20, height=0.35, color="#22c55e", label="Seed 20 AUC")
    ax3.axvline(0.90, color="#ef4444", linestyle="--", linewidth=1.5, label="Leakage Canary Ceiling (0.90)")
    ax3.set_yticks(yh)
    ax3.set_yticklabels(f_names, fontsize=8, color="#e2e8f0")
    ax3.set_xlim(0.45, 0.95)
    ax3.set_xlabel("Single-Feature Symmetric ROC AUC on Withheld Holdout", color="#cbd5e1", fontsize=9)
    ax3.set_title(
        "D. EXP-84-1 Leakage Canary Audit (96 Channels Tested, Max = 0.8060 <= 0.90)",
        color="#f8fafc",
        fontsize=11,
        fontweight="bold",
    )
    leg3 = ax3.legend(loc="lower right", fontsize=8, facecolor="#0f172a", edgecolor="#475569")
    for text in leg3.get_texts():
        text.set_color("#f8fafc")

    fig.suptitle(
        f"GEMSDOE84 Lane H84-THMS — Validated Submission: {card['submission_name']}.tif\n"
        f"Dual-Seed Pooled HOLDOUT-DTI = {card['holdout_dti']['dualseed_pooled_22663px']['dti']:.4f} "
        f"(Seed 30 = {card['holdout_dti']['seed_30_11342px']['dti']:.4f}, "
        f"Seed 20 = {card['holdout_dti']['seed_20_11321px']['dti']:.4f}; 22,663 Withheld Pixels)",
        color="#f8fafc",
        fontsize=11,
        fontweight="bold",
        y=0.985,
    )
    fig.tight_layout(rect=[0.01, 0.01, 0.99, 0.945])

    for d in (ROOT / "figures", ROOT / "docs" / "figures"):
        d.mkdir(parents=True, exist_ok=True)
        out_f = d / "h84_thms_surface_and_dots.png"
        fig.savefig(out_f, dpi=130)
    plt.close(fig)
    print("Saved figures/h84_thms_surface_and_dots.png and docs/figures/h84_thms_surface_and_dots.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
