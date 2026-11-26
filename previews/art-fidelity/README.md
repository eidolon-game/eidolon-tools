# EIDOLON art fidelity review

The [source gallery](../buried-forest/README.md) keeps the original assets available for comparison. This directory contains selected geometry reworks, render comparisons and the manifest for the 22-model surface pass. The GLBs are static candidates for visual review and import testing.

Generate and check the whole original catalog with Python 3.10 or newer, NumPy and Pillow. Use a separate output directory. The 1024 px run requires approximately 280 MB.

```sh
python3 -B scripts/assets/refine_catalog_surfaces.py /path/to/review-output --size 1024
python3 -B scripts/assets/check_catalog_surfaces.py /path/to/review-output
```

The generator embeds base color, tangent normals and packed roughness and metalness. Glass and eyes retain their existing specialized materials. Missing UV channels on textured primitives get a planar projection for visual review. The checker verifies asset provenance, embedded images, textured UV coverage and the unchanged geometry buffers of this surface pass. Review projection seams and texel density on close-ups before use in game.

The geometry reworks are authored independently. Their GLBs keep the original size and functional transforms where applicable. Blender 4.3.2 reimported the static exports. Rig, animation, collision, LODs and visual acceptance in Unreal Engine 5.6 are pending.

The [Catacombs creature gallery](catacombs/README.md) adds eight revised models and 32 matched views. Together with the earlier models below, this brings the geometry pass to 15 of the 22 original assets.

| Asset | Render | 3D model |
| --- | --- | --- |
| Root Stalker | [Before](stalker/RootStalker_reference_close.png) · [After](stalker/RootStalker_reworked_close.png) · [Whole](stalker/RootStalker_reworked_wide.png) | [GLB](stalker/RootStalker_reworked.glb) |
| Riftroot Tangle | [Whole](riftroot/riftroot_tangle.png) · [Fracture detail](riftroot/riftroot_tangle_detail.png) · [Lifted wedge](riftroot/riftroot_tangle_wedge_raised.png) | [GLB](riftroot/riftroot_tangle.glb) |
| Catacomb Crawler | [Whole](crawler/CatacombCrawler.png) | [GLB](crawler/CatacombCrawler.glb) |
| Root Arch | [Before](root-arch/buried_forest_root_arch_before.png) · [After](root-arch/buried_forest_root_arch_after.png) · [Detail](root-arch/buried_forest_root_arch_after_detail.png) | [GLB](root-arch/buried_forest_root_arch_refined.glb) |
| Vein Overlook | [Before](vein-overlook/vein_overlook_balcony_before.png) · [After](vein-overlook/vein_overlook_balcony_after.png) · [Detail](vein-overlook/vein_overlook_balcony_after_detail.png) | [GLB](vein-overlook/vein_overlook_balcony_refined.glb) |
| Valdris recruit sword | [Whole](valdris/valdris_recruit_sword.png) · [Edge detail](valdris/valdris_recruit_sword_edge_review.png) | [GLB](valdris/valdris_recruit_sword.glb) |
| Funerary urn | [Whole](valdris/valdris_funerary_urn.png) · [Lid pivot](valdris/valdris_funerary_urn_lid_review.png) | [GLB](valdris/valdris_funerary_urn.glb) |

[Surface manifest](manifest.json) · [Blender import of the 22 surface candidates](blender-reimport.json) · [Blender import of the seven geometry reworks](geometry-reimport.json)
