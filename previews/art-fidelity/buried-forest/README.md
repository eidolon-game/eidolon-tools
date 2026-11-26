# Buried Forest landmark and mechanism review

These seven GLBs build on the [original Buried Forest gallery](../../buried-forest/README.md) and the [PBR surface pass](../README.md). All comparisons use the same Blender 4.3.2 camera and lights before and after. [Overlook and intake comparison](confronto-foresta.png).

| Asset | Geometry review | Whole model | Close-up | Files |
| --- | --- | --- | --- | --- |
| Oblique Clearing overlook | Layered shale and flaked edges. The central tread passed 35 support rays. | [Before](oblique_clearing_overlook/before.png) · [After](oblique_clearing_overlook/after.png) | [Before](oblique_clearing_overlook/before_detail.png) · [After](oblique_clearing_overlook/after_detail.png) | [GLB](oblique_clearing_overlook/oblique_clearing_overlook.glb) · [Report](oblique_clearing_overlook/verification.json) |
| Branch Terraces ladder | Grain in the rails, wear on the rungs and a chipped stone weight. The 30° hinge test moved the ladder around a fixed axle. | [Before](branch_terrace_ladder/before.png) · [After](branch_terrace_ladder/after.png) | [Before](branch_terrace_ladder/before_detail.png) · [After](branch_terrace_ladder/after_detail.png) | [GLB](branch_terrace_ladder/branch_terrace_ladder.glb) · [Report](branch_terrace_ladder/verification.json) |
| Fern Basin intake and handwheel | Spalled masonry and pitting on cast and forged surfaces. A 90° turn moved the grip while the spindle collar stayed fixed. | [Before](fern_basin_handwheel/before.png) · [After](fern_basin_handwheel/after.png) | [Before](fern_basin_handwheel/before_detail.png) · [After](fern_basin_handwheel/after_detail.png) | [GLB](fern_basin_handwheel/fern_basin_handwheel.glb) · [Report](fern_basin_handwheel/verification.json) |
| Hollow Trunk pin and socket | Bark relief, a worn pull loop and pitted fasteners. The shaft and key cleared the socket in 30 samples over 0.58 m. | [Before](hollow_trunk_pin/before.png) · [After](hollow_trunk_pin/after.png) | [Before](hollow_trunk_pin/before_detail.png) · [After](hollow_trunk_pin/after_detail.png) | [GLB](hollow_trunk_pin/hollow_trunk_pin.glb) · [Report](hollow_trunk_pin/verification.json) |
| Rootlet Canal gate | Weathered ashlar, roots and grate. The gate and counterweight moved 2.25 m in opposing directions and the open passage cleared 56 rays. | [Before](rootlet_canal_gate/before.png) · [After](rootlet_canal_gate/after.png) | [Before](rootlet_canal_gate/before_detail.png) · [After](rootlet_canal_gate/after_detail.png) | [GLB](rootlet_canal_gate/rootlet_canal_gate.glb) · [Report](rootlet_canal_gate/verification.json) |
| Suspended Trunks bridge | Splits in the oak and wear on the treads and fittings. The deck passed 57 support rays. Trunks, posts and yoke cleared the central islet at 19 angles. | [Before](suspended_trunks_bridge/before.png) · [After](suspended_trunks_bridge/after.png) | [Before](suspended_trunks_bridge/before_detail.png) · [After](suspended_trunks_bridge/after_detail.png) | [GLB](suspended_trunks_bridge/suspended_trunks_bridge.glb) · [Report](suspended_trunks_bridge/verification.json) |
| Double Clearing latch | Spalled ashlar and wear in the roots, grip and latch backing. The index tooth cleared the fixed teeth at both seated detents and across 38 positions during retracted travel. | [Before](double_clearing_latch/before.png) · [After](double_clearing_latch/after.png) | [Before](double_clearing_latch/before_detail.png) · [After](double_clearing_latch/after_detail.png) | [GLB](double_clearing_latch/double_clearing_latch.glb) · [Report](double_clearing_latch/verification.json) |

Run from the Tools repository root. The script checks the exported GLB against the original hierarchy, relative transforms and pivot metadata, then tests the reimported geometry in Blender. Use `--samples 0` to verify geometry without rendering or `--asset Name` for a single model. Gallery renders use 20–24 samples.

```sh
python3 -B scripts/assets/refine_catalog_surfaces.py /path/to/pbr --size 1024
python3 -B scripts/assets/check_catalog_surfaces.py /path/to/pbr
blender -b --python-exit-code 1 -t 4 -P environment/refine_forest_mechanisms.py -- /path/to/pbr /path/to/review
```

The models and textures were made in the project. These are detailed source meshes, with up to 312,840 triangles in the bridge. Unreal Engine 5.6 import, gameplay collision, installed movement, and LOD or performance budgets remain to be verified.
