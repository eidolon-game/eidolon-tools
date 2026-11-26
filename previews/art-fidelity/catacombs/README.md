# Catacombs creature review

The eight static GLBs build on the original [Catacombs roster](../../catacombs/README.md) and the [PBR surface pass](../README.md). The comparisons render the original GLB and the revised export in Blender 4.3.2 with matching cameras and lighting. [Rootclaw and Censer Hagfish comparison](confronto-creature.png).

| Creature | Geometry changes | Whole model | Close-up | Files |
| --- | --- | --- | --- | --- |
| Ossuary Tick | Layered scutes and tendons between leg segments | [Before](OssuaryTick/before.png) · [After](OssuaryTick/after.png) | [Before](OssuaryTick/before_detail.png) · [After](OssuaryTick/after_detail.png) | [GLB](OssuaryTick/OssuaryTick.glb) · [Report](OssuaryTick/verification.json) |
| Lintel Mantis | Tapered limb sections, faceted eyes and uneven blade edges | [Before](LintelMantis/before.png) · [After](LintelMantis/after.png) | [Before](LintelMantis/before_detail.png) · [After](LintelMantis/after_detail.png) | [GLB](LintelMantis/LintelMantis.glb) · [Report](LintelMantis/verification.json) |
| Marrow Ram | Chipped cranial wedge, flank scales, hoof wear and shoulder tendons | [Before](MarrowRam/before.png) · [After](MarrowRam/after.png) | [Before](MarrowRam/before_detail.png) · [After](MarrowRam/after_detail.png) | [GLB](MarrowRam/MarrowRam.glb) · [Report](MarrowRam/verification.json) |
| Vault Pincer | Asymmetric claw chips, dorsal plates and joint fibres | [Before](VaultPincer/before.png) · [After](VaultPincer/after.png) | [Before](VaultPincer/before_detail.png) · [After](VaultPincer/after_detail.png) | [GLB](VaultPincer/VaultPincer.glb) · [Report](VaultPincer/verification.json) |
| Censer Hagfish | Radial mouth folds and raised gill lips | [Before](CenserHagfish/before.png) · [After](CenserHagfish/after.png) | [Before](CenserHagfish/before_detail.png) · [After](CenserHagfish/after_detail.png) | [GLB](CenserHagfish/CenserHagfish.glb) · [Report](CenserHagfish/verification.json) |
| Mortar Leech | Pleated feeding collar, worn hooks and holdfasts | [Before](MortarLeech/before.png) · [After](MortarLeech/after.png) | [Before](MortarLeech/before_detail.png) · [After](MortarLeech/after_detail.png) | [GLB](MortarLeech/MortarLeech.glb) · [Report](MortarLeech/verification.json) |
| Rattle Millipede | Reshaped dorsal segments and ridges on the sensory head | [Before](RattleMillipede/before.png) · [After](RattleMillipede/after.png) | [Before](RattleMillipede/before_detail.png) · [After](RattleMillipede/after_detail.png) | [GLB](RattleMillipede/RattleMillipede.glb) · [Report](RattleMillipede/verification.json) |
| Rootclaw | Separate limestone layers on the mantle and claw, exposed claw tendons | [Before](Rootclaw/before.png) · [After](Rootclaw/after.png) | [Before](Rootclaw/before_detail.png) · [After](Rootclaw/after_detail.png) | [GLB](Rootclaw/Rootclaw.glb) · [Report](Rootclaw/verification.json) |

Run from the Tools repository root. The scripts check the size and floor contact against the original, reimport each export and check that its normal-mapped primitives have UVs and tangents. Use `--samples 0` for a geometry-only check or `--asset Name` for an individual creature. The gallery uses 20–24 samples per render.

```sh
python3 -B scripts/assets/refine_catalog_surfaces.py /path/to/pbr --size 1024
python3 -B scripts/assets/check_catalog_surfaces.py /path/to/pbr
blender -b --python-exit-code 1 -t 4 -P scripts/creatures/refine_catacomb_armor.py -- /path/to/pbr /path/to/review
blender -b --python-exit-code 1 -t 4 -P scripts/creatures/refine_catacomb_forms.py -- /path/to/pbr /path/to/review
```

All geometry and materials were made in the project. Unreal 5.6 review, rigging, animation, collision, and LOD budgets remain pending. The static GLBs carry up to 122,180 triangles per creature.
