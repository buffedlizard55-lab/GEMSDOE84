"""Preregistered geological hypotheses for GEMSDOE84 (`Lane H84-THMS`).

Documents the 5 candidate hypotheses (`H84-A` through `H84-E`), naming:
  - specific layers involved,
  - physical signature targeted,
  - why it catches faults missing from the USGS/INGENIOUS catalogue,
  - how it differs from prior GEMSDOE lanes (`GEMSDOE` through `GEMSDOE83`),
  - named non-fault mimicking processes & deconfounding,
  - expected DTI gain & computational cost.
"""
from __future__ import annotations

from typing import Dict, List

H84_HYPOTHESES: List[Dict[str, object]] = [
    {
        "id": "H84-A",
        "lane_code": "H84-THMS",
        "rank": 1,
        "status": "PRIMARY SELECTED & VALIDATED ON DUAL-SEED HOLDOUT",
        "title": "Thermo-Hydro-Mechanical Silica-Seal Fault-Valve, Dual-Scale 1m/10m Fluvial-Scarp Discontinuity & Counterfactual Dual-Head 300m Dinkelbach Allocator",
        "layers": [
            "Official 19-band training_features.tif (Bands 1-19)",
            "DOE GDR #1391 gdr_wellspring_in_footprint.csv (27,092 records: temp_c, geothermquartz_c, geothermchalc_c, geothermcat_c)",
            "DOE GDR #1391 2m_temperature_probe_INGENIOUS_regional_data.zip (3,800 records: T2m, T15m, F2mDAB)",
            "DOE GDR #1391 paleo_geothermal_regional.zip / Paleo_geothermal_final.csv (709 sinter/travertine/silicified-breccia seals)",
            "DOE GDR #1391 gdr_volcanic_vents_in_footprint.csv (21 Quaternary volcanic vents)",
            "USGS GeoDAWN geodawn_rad_u8.tif (K, Th, U, TC) & geodawn_extensions_u8.tif (ThK, UK, UTh, TMI_up150)",
            "USGS 3DEP 1m lidar_scarp_features_u8.tif (12 bands, 75.40% coverage)",
            "USGS 3DEP 10m topo_10m_derived_100m_u8.tif (9 bands, 100% coverage) & dem10_chi_100m_i16/u8.tif (9 bands)",
            "Fold-visible fault catalogue mask (existing_faults.tif with 3-px withhold buffer)",
        ],
        "physical_signature": (
            "(1) Sibson fault-valve silica-seal breach index coupling quartz/chalcedony/Na-K-Ca geothermometer enthalpy, "
            "709 paleo-sinter/travertine fault seals, and 3,800 shallow 2m probe upward conductive heat-flux anomalies "
            "with geodetic transtension and MT clay-cap lateral boundaries; (2) Seamless 1m-LiDAR + 10m-3DEP profile-curvature "
            "and fluvial chi-knickpoint scarp bridge across the 24.60% NE Nevada LiDAR gap; (3) 200 m up-dip (-grad B15) "
            "advected gravity/basement/magnetic-demagnetization step concordance; (4) Counterfactual whole-segment d > 3 px "
            "training of a 3-family (LGBM + ExtraTrees-LGBM + HistGBDT) ensemble with Dual-Head Ridge-Coherent 300 m Dinkelbach allocation."
        ),
        "why_off_catalogue": (
            "Over 39% of Great Basin geothermal systems are blind (Faulds et al., 2011, 2021): silica/travertine self-sealing "
            "and piedmont alluvial fans obscure surface scarps, while 24.60% of the study area lacks 1 m LiDAR. Combining "
            "upward 2m probe heat flux, paleo-sinter seals, geothermometers, up-dip potential-field projection, and 10m "
            "fluvial-chi breaklines recovers both blind geothermal conduits and unmapped relay/piedmont faults."
        ),
        "novelty_vs_prior": (
            "Unifies counterfactual whole-segment d > 3 px training (absent in GEMSDOE82) with 3,800 2m temperature probes, "
            "709 paleo-sinter seals, 10m 3DEP breaklines + fluvial chi-knickpoints across the 24.6% LiDAR gap, 200 m up-dip "
            "advection, and a 3-family Dual-Head Ridge-Coherent Dinkelbach allocator (absent in GEMSDOE83, while also fixing "
            "GEMSDOE83's IR-84-01 cold-cache RuntimeError and IR-84-02 zero-variance CSV column bug)."
        ),
        "named_nonfault_mimic": (
            "Pleistocene Lake Lahontan/Bonneville pluvial shoreline benches, distal lateral thermal outflow plumes in "
            "permeable alluvial fans, and non-tectonic steep canyon walls."
        ),
        "expected_dti_gain": "+0.003 to +0.015 HOLDOUT-DTI over GEMSDOE83 (0.2068) and +0.040+ over GEMSDOE82 (0.1658)",
        "cost": "~65 s CPU on 2 vCPUs, < 1.1 GB peak RSS",
    },
    {
        "id": "H84-B",
        "lane_code": "H84-SCARP-CHI",
        "rank": 2,
        "status": "ABLATED INSIDE 96-CHANNEL STACK",
        "title": "Dual-Scale 1m-LiDAR + 10m-3DEP Fluvial Chi-Knickpoint & Profile-Curvature Seamless Scarp Bridge",
        "layers": [
            "lidar_scarp_features_u8.tif (12 bands)",
            "topo_10m_derived_100m_u8.tif (curv_prof_absmax, slope_p90, hs_lineament, aspect_coherence, relief_local)",
            "dem10_chi_100m_i16.tif (step_max_x1000, ksn_max_m0.9) & dem10_chi_100m_u8.tif (knick_n, raised_n)",
            "detrended_elevation (Band 12), detrended_elevation_slope (Band 19)",
        ],
        "physical_signature": (
            "Relief-normalized 1 m LiDAR scarp excess (step_max, ex_max minus cross_max) seamlessly bridged across "
            "the 24.60% non-LiDAR footprint by 10 m profile curvature breaklines and across-divide fluvial chi-steps."
        ),
        "why_off_catalogue": (
            "Catches degraded < 1.5 m piedmont scarps and active range-front/intrabasin faults inside the 24.60% "
            "NE Nevada 1 m LiDAR gap via 10 m breaklines and drainage base-level knickpoints."
        ),
        "novelty_vs_prior": "Explicit quantile-matched 1m-to-10m scarp + fluvial chi-knickpoint fusion.",
        "named_nonfault_mimic": "Resistant welded-tuff mesa rims and pluvial shoreline bars.",
        "expected_dti_gain": "+0.004 to +0.008 HOLDOUT-DTI contribution",
        "cost": "~10 s CPU",
    },
    {
        "id": "H84-C",
        "lane_code": "H84-UPDIP",
        "rank": 3,
        "status": "ABLATED INSIDE 96-CHANNEL STACK",
        "title": "Up-Dip 60-Deg Basement-Gravity-Magnetic Advected Fault-Plane Coupler",
        "layers": [
            "depth_to_basement (Band 15), iso_gravity_horizontal_gradient (Band 18), iso_gravity_anomaly (Band 13)",
            "mag_reduced_to_pole (Band 2), total_magnetic_intensity (Band 14), geodawn_extensions_u8.tif (TMI_up150)",
        ],
        "physical_signature": (
            "200 m (2.0 px) up-dip advection of hanging-wall gravity HGM, basement gradient, and shallow magnetic "
            "demagnetization along -grad(depth_to_basement)/|grad(depth_to_basement)| coupled with surface scarps."
        ),
        "why_off_catalogue": (
            "60-deg dipping normal faults offset dense/magnetic basement 150-350 m down-dip of the surface trace; "
            "up-dip back-projection aligns buried hanging-wall steps with subtle piedmont surface breaks."
        ),
        "novelty_vs_prior": "Evaluated inside counterfactual whole-segment d > 3 px training.",
        "named_nonfault_mimic": "Pre-Tertiary pluton intrusive contacts and caldera ring margins.",
        "expected_dti_gain": "+0.003 to +0.006 HOLDOUT-DTI contribution",
        "cost": "~8 s CPU",
    },
    {
        "id": "H84-D",
        "lane_code": "H84-RAD-DEMAG",
        "rank": 4,
        "status": "ABLATED INSIDE 96-CHANNEL STACK",
        "title": "Hydrothermal Magnetite-Destruction & K-Metasomatism Radiometric Alteration Corridor",
        "layers": [
            "geodawn_rad_u8.tif (K, Th, U, TC), geodawn_extensions_u8.tif (ThK, UK, UTh, TMI_up150)",
            "total_magnetic_intensity (Band 14), conductivity_surface (Band 17)",
        ],
        "physical_signature": (
            "Shallow hydrothermal magnetite destruction (TMI - TMI_up150 < 0) paired with adularia-sericite "
            "K-metasomatism (K/Th), Uranium redox roll-front halos (U/Th), and MT smectite clay-cap edges."
        ),
        "why_off_catalogue": (
            "Blind hydrothermal upflow zones alter host-rock mineralogy and destroy magnetite in the upper 150 m "
            "even where zero topographic fault scarp exists."
        ),
        "novelty_vs_prior": "Coupled directly with 2m probe heat flux and paleo-sinter seals.",
        "named_nonfault_mimic": "Primary high-K rhyolitic ash-flow tuffs and evaporite playa U accumulation.",
        "expected_dti_gain": "+0.002 to +0.005 HOLDOUT-DTI contribution",
        "cost": "~8 s CPU",
    },
    {
        "id": "H84-E",
        "lane_code": "H84-VALVE-BRIDGE",
        "rank": 5,
        "status": "ABLATED INSIDE 96-CHANNEL STACK",
        "title": "Anisotropic Crack-Tip Wing-Crack & Step-Over Relay Stress Bridge Gated by THM Fault-Valve Breach",
        "layers": [
            "Fold-visible existing_faults.tif (buffer_px = 3)",
            "geodetic_dilatation_rate (Band 8), geodetic_shear_rate (Band 7), geodetic_second_invariant (Band 4)",
            "thm_silica_valve_breach & thm_seamless_scarp_chi",
        ],
        "physical_signature": (
            "12-azimuth structure-tensor continuation cones, facing-tip geometric-mean relay bridges sqrt(F_theta * B_theta), "
            "and tip propagation rays multiplied by the THM silica-valve breach index and seamless 1m/10m scarp-chi composite."
        ),
        "why_off_catalogue": (
            "Distinguishes active displacement-transfer relay ramps and blind splay extensions from geologically dead "
            "fault terminations."
        ),
        "novelty_vs_prior": "Introduces coup_thm_valve_bridge and coup_seamless_scarp_beam interaction channels.",
        "named_nonfault_mimic": "Inactive fault tips where slip genuinely terminates without relay transfer.",
        "expected_dti_gain": "+0.010 to +0.025 HOLDOUT-DTI over static physics alone",
        "cost": "~15 s CPU per fold state",
    },
]
