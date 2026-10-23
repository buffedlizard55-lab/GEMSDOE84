# Candidate Geological Hypotheses for `GEMSDOE84` (`Lane H84-THMS`)

## Overview & Ranking Table

In accordance with the competition research mandate, we formulated **5 new candidate geological hypotheses (`H84-A` through `H84-E`)** not yet implemented across the `GEMSDOE` fleet (`GEMSDOE1`–`GEMSDOE83`). Each hypothesis specifies:
1. Exact data layers involved (`training_features.tif` bands + external GDR/USGS layers),
2. Physical signature targeted,
3. Why it catches faults **missing** from the USGS/INGENIOUS catalogue rather than already-catalogued faults,
4. How it differs from prior implementations (`GEMSDOE32`–`GEMSDOE83`),
5. A named non-fault geological process that could mimic it, and
6. Ranking by expected DTI improvement and implementation cost.

| Rank | ID | Title | Expected `HOLDOUT-DTI` Gain | Implementation Cost | Max Single-Feature Canary AUC (`EXP-84-1`) |
|:---:|---|---|---:|---|---:|
| **1** | **`H84-A`** | **Sibson THM Silica-Seal Fault-Valve Breach Index** (`coup_thm_valve_bridge`) | **`+0.008` to `+0.015`** | Low (`~55` LOC, `O(N)` FFT) | `0.6456` (S30) / `0.6546` (S20) |
| **2** | **`H84-B`** | **Seamless 1m-LiDAR + 10m-3DEP Fluvial-$\chi$ Scarp Bridge** (`coup_seamless_scarp_beam`, `topo10_*`) | **`+0.007` to `+0.013`** | Low (`~60` LOC, cached 10m DEM) | `0.6401` (S30) / `0.6590` (S20) |
| **3** | **`H84-C`** | **3D Gravity-Magnetic Structural Tensor Coaxiality & Basement-Wedge Decoupling** (`pot_gm_coaxiality`) | **`+0.005` to `+0.010`** | Low (`~40` LOC, exact $2\times 2$ eigensystem) | `0.5831` (S30) / `0.5892` (S20) |
| **4** | **`H84-D`** | **Quaternary Dike-Conduit Magmatic-Tectonic Transfer Coupling** (`coup_vent_thm_transfer`) | **`+0.003` to `+0.007`** | Very Low (`~30` LOC) | `0.5412` (S30) / `0.5488` (S20) |
| **5** | **`H84-E`** | **Uranium-Leach / Potassium-Adularia Illite-Smectite Alteration Edge** (`rad_u_leach_k_halo`) | **`+0.002` to `+0.005`** | Very Low (`~25` LOC) | `0.5349` (S30) / `0.5394` (S20) |

---

## Detailed PhD Specification of Each Candidate Hypothesis

### Hypothesis `H84-A` (Rank 1): Sibson Thermo-Hydro-Mechanical (THM) Silica-Seal Fault-Valve Breach Index

- **Layers Involved**:
  - `external/gdr_wellspring_in_footprint.csv` (`27,092` wells/springs: `temp_c`, `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c`)
  - `external/gdr_paleo_geothermal_sinter_travertine.tif` (`709` siliceous sinter & carbonate travertine seal pixels)
  - `external/gdr_2m_temp_probes_100m_i16.tif` (`3,800` shallow 2-meter temperature probe measurements)
  - `external/geodetic_strain_100m_u8.tif` (3-band GPS dilatational, shear, and transtensional strain rate)
  - `training_features.tif` Bands 12–14 (3D Magnetotelluric electrical resistivity at `1,000 m`, `2,000 m`, and `4,000 m`)
  - Fold-visible structural relay bridge & directional tip beams (`net_bridge_med`, `net_bridge_long`, `net_beam_med`)
- **Physical Signature Targeted**:
  Co-located chemical geothermometer reservoir temperature excess ($\max(T_{\text{quartz}}, T_{\text{chalcedony}}, T_{\text{Na-K-Ca}}) > 80^\circ\text{C}$), shallow 2 m conductive heat-flux anomaly, and surface paleo-sinter precipitation perched on the brittle flanks of low-resistivity smectite clay caps (`1–2 km` MT conductor over `4 km` resistive root) inside high-transtension step-over relays ($400\text{ m–}4.0\text{ km}$).
- **Why It Catches Unmapped Faults Rather Than Already-Catalogued Faults**:
  Under Sibson's (1990, 2000) fault-valve mechanism, hydrothermal silica (`SiO2`) and calcite precipitate rapidly following microseismic pressure drops, cementing surface fault scarps against erosion or burying them beneath aggrading sinter aprons and playa evaporites. Consequently, photogeologic and airphoto-based fault compilers (USGS Qfaults / NBMG) systematically miss sealed hydrothermal transfer faults inside step-over basins, whereas aqueous silica/cation geothermometers (`gdr_wellspring_in_footprint.csv`) and 2 m shallow temperature probes directly sample fluid upflow escaping from the active subsurface fault valve.
- **How It Differs From Prior Implementations (`GEMSDOE32`–`GEMSDOE83`)**:
  1. `GEMSDOE83` suffered from **`IR-84-02`**: its `_rasterize_geothermal_and_vents` queried nonexistent CSV column headers (`utm_e`, `utm_n`, `gt_quartz_c`, `gt_chalc_c`, `gt_nak_c`), silently producing **all-zero geothermal channels** on cold builds. `GEMSDOE84` fixes this bug and uses the true `row`, `col`, `temp_c`, `geothermquartz_c`, `geothermchalc_c`, and `geothermcat_c` columns.
  2. No prior repo ingested `gdr_paleo_geothermal_sinter_travertine.tif` (`709` pixels) or `gdr_2m_temp_probes_100m_i16.tif` (`3,800` pixels) or coupled them with fold-visible step-over relay bridges (`coup_thm_valve_bridge`).
- **Named Non-Fault Geological Mimic**:
  Stratiform lateral outflow plumes in permeable perched alluvial aquifers or paleo-lacustrine tufa shorelines (e.g., Lake Lahontan highstand tufa terraces) displaced down-gradient from the actual feeder fault.

---

### Hypothesis `H84-B` (Rank 2): Seamless 1m-LiDAR + 10m-3DEP Fluvial-$\chi$ Scarp Bridge

- **Layers Involved**:
  - `external/lidar_scarp_features_u8.tif` (6-band 1 m USGS 3DEP LiDAR sub-100m scarp sharpness, directional anisotropy, slope P90, roughness)
  - `external/topo_10m_derived_100m_u8.tif` (4-band 10 m USGS 3DEP sub-100m slope max, roughness, profile curvature, plan curvature)
  - `external/dem10_chi_100m_i16.tif` and `external/dem10_chi_100m_u8.tif` (4-band 10 m drainage-network $\chi$-coordinate, across-divide $\Delta\chi$ gradient, local relief, hack-index anomaly)
  - `training_features.tif` Band 1 (100 m land elevation)
  - Fold-visible tip beams (`net_beam_med`, `net_beam_long`, `net_tip_ray`)
- **Physical Signature Targeted**:
  High-frequency profile-curvature scarp breaklines and across-divide fluvial $\chi$-knickpoint disequilibrium aligned along the projected strike beams ($400\text{ m–}2.5\text{ km}$) of terminating fault segments across gentle alluvial bajadas ($\text{slope} \le 6^\circ$).
- **Why It Catches Unmapped Faults Rather Than Already-Catalogued Faults**:
  Range-front master faults (`slope > 12°`) are nearly completely mapped in the USGS/INGENIOUS catalogue, whereas synthetic piedmont splays and basinward relay faults produce low-amplitude ($0.5\text{–}2.5\text{ m}$) scarps smoothed out by the 100 m competition DEM (`Band 1`). Furthermore, `lidar_scarp_features_u8.tif` is missing across **`24.60%` of the active footprint** (`1,271,174` cells in NE Nevada, `IR-84-06`). Bridging 1 m LiDAR where available with 10 m 3DEP profile curvature and drainage $\chi$-disequilibrium creates the first `100%`-coverage sub-100m scarp detector (`coup_seamless_scarp_beam`).
- **How It Differs From Prior Implementations**:
  `GEMSDOE81`–`GEMSDOE83` relied solely on `lidar_scarp_features_u8.tif` (leaving `24.60%` of the footprint unrepresented at sub-100m scale) and never incorporated `topo_10m_derived_100m_u8.tif` or `dem10_chi_100m_i16.tif`.
- **Named Non-Fault Geological Mimic**:
  Pleistocene pluvial Lake Lahontan wave-cut recession shorelines and incised alluvial-fan terrace risers that parallel basin contours without underlying tectonic displacement.

---

### Hypothesis `H84-C` (Rank 3): 3D Gravity-Magnetic Structural Tensor Coaxiality & Basement-Wedge Decoupling

- **Layers Involved**:
  - `training_features.tif` Bands 4–5 (CBA and Isostatic Gravity)
  - `training_features.tif` Bands 6–11 (Gravity Horizontal Gradient Magnitude, Tilt Derivative, Upward Continuation `2 km`, Magnetic Anomaly, Magnetic HGM, Magnetic Tilt Derivative)
  - `training_features.tif` Band 15 (Depth to Mesozoic Basement)
- **Physical Signature Targeted**:
  Coaxial alignment ($\cos 2(\theta_g - \theta_m) \to +1$) of the principal eigenvector orientations of the smoothed 2D gravity and magnetic horizontal-gradient structure tensors, weighted by the basement-wedge tilt gradient $|\nabla Z_{\text{basement}}|$ inside low-slope Quaternary valleys.
- **Why It Catches Unmapped Faults Rather Than Already-Catalogued Faults**:
  Intrabasin accommodation zones and buried horst-graben bounding faults beneath $500\text{–}2,500\text{ m}$ of unconsolidated Neogene valley fill have zero surface topographic expression and are therefore invisible to airphoto/DEM fault mapping. However, where a single steep basement fault juxtaposes both density and magnetic susceptibility contrasts, the gravity and magnetic horizontal-gradient structure tensors become strictly coaxial along strike (`pot_gm_coaxiality`).
- **How It Differs From Prior Implementations**:
  Prior repos computed scalar magnitude products ($|\nabla g| \cdot |\nabla m|$) or raw dot products without computing the smoothed $2\times 2$ multi-scale structure-tensor eigensystems of both potential fields and their double-angle coaxiality invariant $\cos 2(\theta_g - \theta_m)$.
- **Named Non-Fault Geological Mimic**:
  Buried Jurassic/Cretaceous granitoid pluton Roof-Pendant intrusive contacts or Oligocene caldera ring-fracture margins with concordant density and susceptibility contrasts but no Quaternary reactivation.

---

### Hypothesis `H84-D` (Rank 4): Quaternary Dike-Conduit Magmatic-Tectonic Transfer Coupling

- **Layers Involved**:
  - `external/gdr_volcanic_vents_in_footprint.csv` (`21` Pleistocene-Holocene volcanic vents inside footprint with exact `row,col` coordinates)
  - `training_features.tif` Bands 9–11 (Magnetic Anomaly, Magnetic HGM, Magnetic Tilt Derivative)
  - `external/geodetic_strain_100m_u8.tif` (GPS shear + dilatational strain)
  - Fold-visible step-over relay bridges (`net_bridge_med`, `net_bridge_long`)
- **Physical Signature Targeted**:
  Linear high-magnetic-tilt dike swarms linking Quaternary volcanic vents across extensional fault step-overs (`coup_vent_thm_transfer`).
- **Why It Catches Unmapped Faults Rather Than Already-Catalogued Faults**:
  Basaltic and bimodal feeder dikes intrude perpendicular to $\sigma_3$ along nascent extensional transfer faults. Where post-eruptive basaltic talus aprons or eolian sand sheets bury the surface fault trace, surface fault compilers map the volcanic cone as a point feature while missing the underlying fault-dike transfer corridor.
- **How It Differs From Prior Implementations**:
  In `GEMSDOE83`, `_rasterize_geothermal_and_vents` checked for `"utm_e" in df.columns` on `gdr_volcanic_vents_in_footprint.csv` (whose actual columns are `row,col,lat,lon`), causing all `21` volcanic vents to be silently skipped (`vent_dist = 0` everywhere, `IR-84-02`). `GEMSDOE84` fixes this bug and couples the true volcanic vent proximity field with magnetic tilt ridges and step-over bridges.
- **Named Non-Fault Geological Mimic**:
  Topographically channeled basaltic lava flows filling paleovalleys down-slope from a cinder cone, creating elongated magnetic highs that follow paleodrainage rather than a feeder fault.

---

### Hypothesis `H84-E` (Rank 5): Radiometric Uranium-Leach / Potassium-Adularia Alteration Halo

- **Layers Involved**:
  - `external/geodawn_rad_u8.tif` (3-band USGS GeoDAWN airborne gamma-ray spectrometry: Potassium `%K`, equivalent Thorium `eTh`, equivalent Uranium `eU`)
  - `external/geodawn_extensions_u8.tif` (high-resolution aeromagnetic & radiometric ratios)
  - `training_features.tif` Bands 12–13 (`1 km` and `2 km` MT resistivity)
  - `training_features.tif` Band 2 (land slope)
- **Physical Signature Targeted**:
  Potassium enrichment (`%K / eTh` adularia-illite metasomatism) coupled with localized Uranium redox mobilization (`eU / eTh` gradient) along low-slope range-front piedmonts underlain by shallow MT conductors (`rad_u_leach_k_halo`).
- **Why It Catches Unmapped Faults Rather Than Already-Catalogued Faults**:
  Blind upflow of neutral-chloride and bicarbonate geothermal fluids along unmapped piedmont faults alters primary plagioclase to potassium adularia/illite (`+K`) while oxidizing and mobilizing hexavalent uranium (`U(VI)`) across the redox front (`|\nabla(eU/eTh)|`) even when no discrete morphological scarp is preserved.
- **How It Differs From Prior Implementations**:
  Prior lanes included raw `geodawn_rad_u8` bands (`K`, `eTh`, `eU`) and simple pairwise differences (`K - Th`) without constructing the alteration-specific `K/Th × |∇(U/Th)|` redox-metasomatic edge coupled to shallow MT conductivity.
- **Named Non-Fault Geological Mimic**:
  Detrital arkosic alluvial fans shed from high-K felsic ash-flow tuffs or evaporitic playa-margin uranium roll-front accumulations unrelated to Quaternary faulting.
