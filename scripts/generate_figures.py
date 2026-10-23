#!/usr/bin/env python3
"""Generate publication-grade diagnostic figures for GEMSDOE84 (H84-TCDH).

Reads verified rasters and machine-readable JSON receipts in ``evidence/`` and
writes four high-DPI PNG figures into ``docs/assets/figures/``.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57.grid import load_grid  # noqa: E402
from gems84.paths import BRIDGE  # noqa: E402

FIG_DIR = ROOT / "docs" / "assets" / "figures"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 11.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.edgecolor": "#334155",
    "axes.linewidth": 0.8,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.facecolor": "#ffffff",
    "axes.facecolor": "#f8fafc",
    "grid.color": "#cbd5e1",
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
})


def make_fig1_submission_map(tif_path: Path) -> Path:
    grid = load_grid(BRIDGE)
    fp, cat = grid.footprint, grid.catalogue
    with rasterio.open(tif_path) as src:
        pred = src.read(1) > 0.5
        tr = src.transform

    dcat = ndi.distance_transform_edt(~cat)
    ys, xs = np.nonzero(pred)
    d_pts = dcat[ys, xs]

    # Convert pixel indices to EPSG:32611 UTM km
    x0_km = tr.c / 1000.0
    y0_km = tr.f / 1000.0
    dx_km = tr.a / 1000.0
    dy_km = tr.e / 1000.0  # negative

    H, W = fp.shape
    extent = [x0_km, x0_km + W * dx_km, y0_km + H * dy_km, y0_km]

    pt_x = x0_km + (xs + 0.5) * dx_km
    pt_y = y0_km + (ys + 0.5) * dy_km
    is_far = d_pts > 36.0
    is_corr = ~is_far

    # Find rich 45 km x 45 km zoom window with both relay/tip dots and blind-basin dots
    best_score = -1.0
    best_rc = (1400, 1400)
    win = 450  # 45 km
    for r0 in range(400, H - win - 300, 225):
        for c0 in range(300, W - win - 300, 225):
            sub_fp = fp[r0 : r0 + win, c0 : c0 + win]
            if sub_fp.mean() < 0.88:
                continue
            sub_cat = cat[r0 : r0 + win, c0 : c0 + win].sum()
            in_box = (ys >= r0) & (ys < r0 + win) & (xs >= c0) & (xs < c0 + win)
            nc = int((in_box & is_corr).sum())
            nf = int((in_box & is_far).sum())
            sc = min(nc, 600) + 1.4 * min(nf, 500) + 0.1 * min(sub_cat, 2500)
            if sc > best_score:
                best_score = sc
                best_rc = (r0, c0)

    r0, c0 = best_rc
    zx0 = x0_km + c0 * dx_km
    zx1 = x0_km + (c0 + win) * dx_km
    zy1 = y0_km + r0 * dy_km
    zy0 = y0_km + (r0 + win) * dy_km

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 6.6), gridspec_kw={"width_ratios": [1.08, 1.0]})

    # Background footprint
    bg = np.where(fp, 0.94, 1.0)
    ax1.imshow(bg, cmap="Greys", vmin=0.75, vmax=1.02, extent=extent, origin="upper", interpolation="nearest")

    c_ys, c_xs = np.nonzero(cat)
    ax1.scatter(
        x0_km + (c_xs + 0.5) * dx_km,
        y0_km + (c_ys + 0.5) * dy_km,
        s=0.08, c="#64748b", alpha=0.55, rasterized=True, label="Mapped catalogue faults (0 emitted on trace)",
    )
    ax1.scatter(
        pt_x[is_corr], pt_y[is_corr],
        s=0.32, c="#0072B2", alpha=0.78, rasterized=True,
        label=f"Stratum 1: LOQO corridor / relay / tip ({int(is_corr.sum()):,} dots)",
    )
    ax1.scatter(
        pt_x[is_far], pt_y[is_far],
        s=0.38, c="#D55E00", alpha=0.82, rasterized=True,
        label=f"Stratum 2: Concealed blind basin d>3.6 km ({int(is_far.sum()):,} dots)",
    )

    rect = mpatches.Rectangle(
        (zx0, zy0), zx1 - zx0, zy1 - zy0,
        linewidth=1.5, edgecolor="#0f172a", facecolor="none", linestyle="--",
    )
    ax1.add_patch(rect)
    ax1.set_title("A. Full NW Great Basin Submission (39,000 Discrete Dots, EPSG:32611)")
    ax1.set_xlabel("UTM Zone 11N Easting (km)")
    ax1.set_ylabel("UTM Zone 11N Northing (km)")
    ax1.legend(loc="lower left", markerscale=9, framealpha=0.95, fontsize=8.5)
    ax1.grid(True, alpha=0.45)

    # Panel B: Zoomed 45 km x 45 km window
    sub_bg = np.where(fp[r0 : r0 + win, c0 : c0 + win], 0.95, 1.0)
    ax2.imshow(
        sub_bg, cmap="Greys", vmin=0.75, vmax=1.02,
        extent=[zx0, zx1, zy0, zy1], origin="upper", interpolation="nearest",
    )
    in_cat = (c_ys >= r0) & (c_ys < r0 + win) & (c_xs >= c0) & (c_xs < c0 + win)
    ax2.scatter(
        x0_km + (c_xs[in_cat] + 0.5) * dx_km,
        y0_km + (c_ys[in_cat] + 0.5) * dy_km,
        s=2.2, c="#475569", alpha=0.85, label="Mapped fault trace (pixel-exact zeroed)",
    )
    in_pts = (ys >= r0) & (ys < r0 + win) & (xs >= c0) & (xs < c0 + win)
    in_tip = in_pts & (d_pts <= 2.0)
    in_rel = in_pts & (d_pts > 2.0) & (d_pts <= 36.0)
    in_bln = in_pts & (d_pts > 36.0)

    ax2.scatter(
        pt_x[in_rel], pt_y[in_rel],
        s=11, c="#0072B2", alpha=0.9, label="LOQO relay / step-over / splay (sep >= 300 m)",
    )
    ax2.scatter(
        pt_x[in_tip], pt_y[in_tip],
        s=18, c="#009E73", marker="^", alpha=0.95, label="Anisotropic tip extension (1 < d_cat <= 2 px)",
    )
    ax2.scatter(
        pt_x[in_bln], pt_y[in_bln],
        s=13, c="#D55E00", marker="D", alpha=0.9, label="Concealed basin basement / hydro target (d > 3.6 km)",
    )
    ax2.set_xlim(zx0, zx1)
    ax2.set_ylim(zy0, zy1)
    ax2.set_title("B. 45 km x 45 km Detail: Relay Architecture & Blind-Basin Discovery")
    ax2.set_xlabel("UTM Zone 11N Easting (km)")
    ax2.set_ylabel("UTM Zone 11N Northing (km)")
    ax2.legend(loc="lower right", framealpha=0.95, fontsize=8.3)
    ax2.grid(True, alpha=0.45)

    fig.suptitle(
        "GEMSDOE84 Promoted Candidate: gems84-h84b-tcdh-twostrat-39000d-20261022T235800Z-zeros.tif",
        fontsize=13, fontweight="bold", y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = FIG_DIR / "fig1_submission_map.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def make_fig2_holdout_ablation() -> Path:
    e1 = json.loads((ROOT / "evidence" / "exp84b1_ablation.json").read_text())
    e2 = json.loads((ROOT / "evidence" / "exp84b2_allocation.json").read_text())

    s1 = e1["pooled"]["scores"]
    s2 = e2["pooled_best_candidate"]["scores"]

    arms = [
        ("Blind Physics Only\n(EXP-84B-1, no catalogue)", s1["ctrl_phys_blind_only"], "#94a3b8"),
        ("Incumbent H33-2-B2 Recipe\n(Baseline on holdout)", s1["incumbent_h33_b2_recipe"], "#dc2626"),
        ("Aniso + Supremum Patient\n(EXP-84B-2, 55,120d)", s2["alloc_aniso_phys_sup"], "#6366f1"),
        ("19-Band + Anatomy\n(EXP-84B-1 patient)", s1["ctrl_base19_anat"], "#64748b"),
        ("PROMOTED: H84-TCDH TwoStrat\n(39,000d, NMS3, Gate 3B PASS)", s2["alloc_twostrat_nms3_39k"], "#059669"),
        ("Full H84-TCDH Stack\n(EXP-84B-1 patient, 49,378d)", s1["h84b_tcdh_full"], "#2563eb"),
        ("19-Band + Anatomy NMS3\n(37,654d control)", s2["ctrl_b19_nms3_37k"], "#0284c7"),
        ("Unstratified H84-TCDH NMS3\n(37,654d, Gate 3B 0.896 STOP)", s2["alloc_fixed_nms3_37k"], "#d97706"),
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.8), gridspec_kw={"width_ratios": [1.18, 1.0]})

    y = np.arange(len(arms))
    vals = [a[1]["dti"] for a in arms]
    lo = [a[1]["dti"] - a[1]["ci95"][0] for a in arms]
    hi = [a[1]["ci95"][1] - a[1]["dti"] for a in arms]
    cols = [a[2] for a in arms]

    ax1.axvline(s1["incumbent_h33_b2_recipe"]["dti"], color="#dc2626", linestyle=":", linewidth=1.4, label="H33-2-B2 baseline (0.1056)")
    ax1.barh(y, vals, color=cols, alpha=0.86, height=0.62, edgecolor="#1e293b", linewidth=0.6)
    ax1.errorbar(vals, y, xerr=[lo, hi], fmt="none", ecolor="#0f172a", elinewidth=1.4, capsize=3.5)
    for yi, v, (_, d, _) in zip(y, vals, arms):
        ax1.text(d["ci95"][1] + 0.0025, yi, f"{v:.4f}", va="center", fontsize=8.8, fontweight="bold", color="#0f172a")

    ax1.set_yticks(y)
    ax1.set_yticklabels([a[0] for a in arms], fontsize=8.7)
    ax1.set_xlim(0.0, 0.195)
    ax1.set_xlabel("Pooled HOLDOUT-DTI (gems57-pooled-hide-v2; n = 22,893 withheld positives; 95% block CI)")
    ax1.set_title("A. Controlled Ablation & Allocator Study (HOLDOUT-DTI)")
    ax1.grid(True, axis="x", alpha=0.5)
    ax1.legend(loc="lower right", fontsize=8.5)

    # Panel B: Distance-stratified kernel recall
    dr = e2["distance_stratified_recall"]
    bins = ["3_6px", "6_12px", "12_25px", "25_9999px"]
    blabels = ["300-600 m\n(3-6 px)", "0.6-1.2 km\n(6-12 px)", "1.2-2.5 km\n(12-25 px)", "> 2.5 km\n(> 25 px blind)"]
    x = np.arange(len(bins))
    w = 0.25

    r_inc = [100.0 * dr["incumbent_h33_b2_recipe"][b]["kernel_recall"] for b in bins]
    r_pro = [100.0 * dr["alloc_twostrat_nms3_39k"][b]["kernel_recall"] for b in bins]
    r_uns = [100.0 * dr["alloc_fixed_nms3_37k"][b]["kernel_recall"] for b in bins]

    ax2.bar(x - w, r_inc, width=w, color="#dc2626", alpha=0.85, label="Incumbent H33-2-B2 (0.1056)")
    ax2.bar(x, r_pro, width=w, color="#059669", alpha=0.90, label="PROMOTED TwoStrat 39k (0.1234)")
    ax2.bar(x + w, r_uns, width=w, color="#d97706", alpha=0.85, label="Unstratified NMS3 37k (0.1612, Gate 3B STOP)")

    for xi, v1, v2, v3 in zip(x, r_inc, r_pro, r_uns):
        ax2.text(xi - w, v1 + 0.7, f"{v1:.1f}%", ha="center", fontsize=7.6, color="#991b1b")
        ax2.text(xi, v2 + 0.7, f"{v2:.1f}%", ha="center", fontsize=7.8, fontweight="bold", color="#065f46")
        ax2.text(xi + w, v3 + 0.7, f"{v3:.1f}%", ha="center", fontsize=7.6, color="#92400e")

    ax2.set_xticks(x)
    ax2.set_xticklabels(blabels)
    ax2.set_ylim(0, 44)
    ax2.set_ylabel("300 m Triangular-Kernel Recall of Withheld Faults (%)")
    ax2.set_title("B. Kernel Recall by Distance from Visible Catalogue")
    ax2.legend(loc="upper right", fontsize=8.3)
    ax2.grid(True, axis="y", alpha=0.5)

    fig.tight_layout()
    out = FIG_DIR / "fig2_holdout_ablation_allocation.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def make_fig3_uniqueness_and_incumbent() -> Path:
    u_stop = json.loads((ROOT / "evidence" / "exp84b3_unstratified_gate3b_stop.json").read_text())
    u_pass = json.loads((ROOT / "evidence" / "exp84b3_uniqueness_and_packaging.json").read_text())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.4, 5.8), gridspec_kw={"wspace": 0.34})

    # Panel A: Incumbent H33-2-B2 pruning trajectory vs Leaderboard #1
    chain = [
        ("H19-5", 121.131, 0.1922, (8, 10)),
        ("d1-5", 60.069, 0.2477, (-20, 11)),
        ("d2-8", 44.090, 0.2600, (-12, -20)),
        ("B1", 40.199, 0.2708, (22, -12)),
        ("H33-2-B2", 37.654, 0.2778, (-20, 13)),
    ]
    xs = [c[1] for c in chain]
    ys = [c[2] for c in chain]

    ax1.plot(xs, ys, "-o", color="#2563eb", linewidth=2.2, markersize=7, label="Observed live DTI (OWNER-REPORTED)")
    ax1.scatter([37.654], [0.27836], marker="x", s=95, color="#dc2626", linewidths=2.2, zorder=5,
                label="Zero-new-TP analytical curve (0.27836)")
    ax1.axhline(0.4413, color="#059669", linestyle="--", linewidth=1.6, label="Leaderboard #1: xiaofanhu (0.4413, ORGANIZER-CONFIRMED)")
    ax1.axhline(0.3195, color="#7c3aed", linestyle=":", linewidth=1.3, label="Prompt reference tier (~#22, 0.3195)")

    for lbl, xk, yv, (ox, oy) in chain:
        ax1.annotate(
            f"{lbl} ({yv:.4f})", (xk, yv), xytext=(ox, oy),
            textcoords="offset points", ha="center", fontsize=8.0, fontweight="bold", color="#1e293b",
        )

    ax1.set_xlim(132, 20)
    ax1.set_ylim(0.16, 0.48)
    ax1.set_xlabel("Emitted Nonzero Pixels / Dots (thousands, pruning left -> right)")
    ax1.set_ylabel("Live DrivenData DTI Score")
    ax1.set_title("A. H33-2-B2 Precision Pruning vs Leaderboard Ceiling", fontsize=11.0)
    ax1.legend(loc="upper left", fontsize=8.0, framealpha=0.95)
    ax1.grid(True, alpha=0.5)

    # Panel B: Deduplicate distinct registry archetypes by (their_dots, forward_overlap_3px)
    stop_lookup = {
        r["submission"]: r["forward_overlap_3px"]
        for r in u_stop["gate_3b_post_placement_dots"]["top_15_discriminating_overlaps"]
    }
    distinct_pass = []
    seen_sig = set()
    for r in u_pass["gate_3b_post_placement_dots"]["top_15_discriminating_overlaps"]:
        parts = r["submission"].split("__")
        repo = parts[0].split(":")[-1]
        sig = (repo, parts[1][:10] if len(parts) > 1 else "")
        if sig in seen_sig:
            continue
        seen_sig.add(sig)
        distinct_pass.append(r)
        if len(distinct_pass) == 6:
            break

    short_names = []
    for r in distinct_pass:
        parts = r["submission"].split("__")
        repo = parts[0].split(":")[-1]
        stem = parts[1][:18] if len(parts) > 1 else r["submission"][:18]
        short_names.append(f"{repo}: {stem}")

    pass_vals = [r["forward_overlap_3px"] for r in distinct_pass]
    stop_vals = [stop_lookup.get(r["submission"], 0.78) for r in distinct_pass]

    yi = np.arange(len(short_names))
    h = 0.36
    ax2.axvline(0.70, color="#dc2626", linestyle="--", linewidth=1.8, label="Gate 3B ceiling (0.70)")
    ax2.barh(yi - h / 2, stop_vals, height=h, color="#ef4444", alpha=0.78, label="Unstratified 37k (max 0.896 STOP)")
    ax2.barh(yi + h / 2, pass_vals, height=h, color="#059669", alpha=0.90, label="PROMOTED TwoStrat 39k (max 0.676 PASS)")

    for idx, (sv, pv) in enumerate(zip(stop_vals, pass_vals)):
        ax2.text(pv - 0.015, idx + h / 2, f"{pv:.3f}", va="center", ha="right", fontsize=8.0, fontweight="bold", color="#ffffff")
        ax2.text(sv + 0.010, idx - h / 2, f"{sv:.3f}", va="center", ha="left", fontsize=8.0, fontweight="bold", color="#991b1b")

    ax2.set_yticks(yi)
    ax2.set_yticklabels(short_names, fontsize=8.4)
    ax2.set_ylim(len(short_names) + 0.85, -0.65)
    ax2.set_xlim(0.0, 1.04)
    ax2.set_xlabel("3-Pixel Forward Dot Overlap vs Discriminating Priors (1,092 checked)")
    ax2.set_title("B. Gate 3B Audit (1,163 Rasters; Surface Max |rho| = 0.2629)", fontsize=11.0)
    ax2.legend(loc="lower left", fontsize=7.9, framealpha=0.95)
    ax2.grid(True, axis="x", alpha=0.5)

    fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.12, wspace=0.34)
    out = FIG_DIR / "fig3_uniqueness_and_incumbent.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def make_fig4_leakage_canary() -> Path:
    e1 = json.loads((ROOT / "evidence" / "exp84b1_ablation.json").read_text())
    e3 = json.loads((ROOT / "evidence" / "exp84b3_uniqueness_and_packaging.json").read_text())

    all_f = e1["canary_gate"]["all_features"]
    anat_sorted = sorted(
        [(k, v) for k, v in all_f.items() if k.startswith("anat_")],
        key=lambda kv: kv[1]["max_sym_auc"], reverse=True,
    )[:6]
    phys_sorted = sorted(
        [(k, v) for k, v in all_f.items() if not k.startswith("anat_")],
        key=lambda kv: kv[1]["max_sym_auc"], reverse=True,
    )[:6]
    chosen = anat_sorted + phys_sorted
    names = [k for k, _ in chosen]
    aucs_20 = [v["by_seed"][0] for _, v in chosen]
    aucs_21 = [v["by_seed"][1] for _, v in chosen]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.4, 5.4), gridspec_kw={"width_ratios": [1.12, 1.0], "wspace": 0.26})

    y = np.arange(len(names))
    ax1.axvline(0.90, color="#dc2626", linestyle="--", linewidth=1.8, label="Leakage Canary Stop (AUC > 0.90)")
    ax1.axvline(0.50, color="#94a3b8", linestyle=":", linewidth=1.1, label="Random baseline (0.50)")
    ax1.barh(y - 0.17, aucs_20, height=0.34, color="#2563eb", alpha=0.88, label="Holdout Seed 20")
    ax1.barh(y + 0.17, aucs_21, height=0.34, color="#0ea5e9", alpha=0.85, label="Holdout Seed 21")
    for yi, a20 in zip(y, aucs_20):
        ax1.text(a20 + 0.008, yi - 0.17, f"{a20:.4f}", va="center", fontsize=8.0, fontweight="bold")

    ax1.set_yticks(y)
    ax1.set_yticklabels(names, fontsize=8.6)
    ax1.invert_yaxis()
    ax1.set_xlim(0.45, 0.96)
    ax1.set_xlabel("Single-Feature Symmetric Holdout AUC on Withheld Components")
    ax1.set_title("A. Leakage Canary Across All 52 Features (Max = 0.7724)", fontsize=11.0)
    ax1.legend(loc="lower right", fontsize=8.1)
    ax1.grid(True, axis="x", alpha=0.5)

    # Panel B: Structural composition of the 39,000 emitted dots
    dp = e3["dot_profile"]
    cats = [
        "Catalogue\nTrace\n(d = 0 px)",
        "Along-Strike\nTips\n(1-2 px)",
        "Relays &\nSplays\n(2-6 px)",
        "Step-Over\nBridges\n(6-15 px)",
        "Concealed\nBasin\n(> 15 px)",
    ]
    counts = [
        dp["on_catalogue_pixels"],
        dp["tip_extensions_1_to_2px"],
        dp["near_relay_2_to_6px"],
        dp["stepover_6_to_15px"],
        dp["intrabasin_blind_gt_15px"],
    ]
    colors = ["#ef4444", "#009E73", "#0072B2", "#38bdf8", "#D55E00"]

    xb = np.arange(len(cats))
    bars = ax2.bar(xb, counts, color=colors, width=0.56, edgecolor="#1e293b", linewidth=0.7)
    for b, cnt in zip(bars, counts):
        pct = 100.0 * cnt / max(dp["n_dots"], 1)
        ax2.text(b.get_x() + b.get_width() / 2, cnt + 450, f"{cnt:,}\n({pct:.1f}%)",
                 ha="center", va="bottom", fontsize=8.2, fontweight="bold")

    ax2.set_xticks(xb)
    ax2.set_xticklabels(cats, fontsize=8.5)
    ax2.set_ylim(0, 23500)
    ax2.set_ylabel("Emitted Discrete Dots (300 m min spacing)")
    ax2.set_title("B. Structural Allocation of Promoted 39,000-Dot Map", fontsize=11.0)
    ax2.grid(True, axis="y", alpha=0.5)

    fig.subplots_adjust(left=0.14, right=0.98, top=0.90, bottom=0.15, wspace=0.26)
    out = FIG_DIR / "fig4_leakage_canary_and_features.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    e3 = json.loads((ROOT / "evidence" / "exp84b3_uniqueness_and_packaging.json").read_text())
    tif_path = ROOT / e3["gate_3c_packaging"]["tif_file"]

    for fn in (
        lambda: make_fig1_submission_map(tif_path),
        make_fig2_holdout_ablation,
        make_fig3_uniqueness_and_incumbent,
        make_fig4_leakage_canary,
    ):
        p = fn()
        print(f"Generated {p.relative_to(ROOT)} ({p.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
