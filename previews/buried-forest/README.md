# Buried Forest previews

| Asset | Preview | Authoring source |
| --- | --- | --- |
| Root Stalker | [Render](RootStalker.png) · [GLB](RootStalker.glb) | [Blender generator](../../scripts/creatures/make_root_stalker.py) |
| Root Arch | [Render](buried_forest_root_arch.png) · [GLB](buried_forest_root_arch.glb) | [Blender generator](../../environment/build_buried_forest_arch.py) |
| Oblique Clearing overlook | [Render](oblique_clearing_overlook.png) · [GLB](oblique_clearing_overlook.glb) | [Blender generator](../../environment/build_oblique_clearing_overlook.py) |
| Branch Terraces ladder | [Render](branch_terrace_ladder.png) · [GLB](branch_terrace_ladder.glb) | [Blender generator](../../environment/build_branch_terrace_ladder.py) |
| Buried Forest ambience | [WAV](ambience/sfx_amb_buried_forest.wav) · [Manifest](ambience/manifest.json) | [Audio generator](../../scripts/audio/render_buried_forest_ambience.py) |
| Fern Basin mechanisms | [Handwheel](fern-basin/sfx_fern_basin_handwheel_actuate.wav) · [Drain release](fern-basin/sfx_fern_basin_drain_release.wav) · [Manifest](fern-basin/manifest.json) | [Audio generator](../../scripts/audio/render_fern_basin_cues.py) |
| Fern Basin intake and handwheel | [Render](fern-basin/fern_basin_handwheel.png) · [GLB](fern-basin/fern_basin_handwheel.glb) | [Blender generator](../../environment/build_fern_basin_handwheel.py) |

The Root Stalker stands approximately 2.94 m tall. Its layered bark, hooked limbs and exposed joint membranes are visible in the render. The arch is approximately 2.96 m wide and 4.14 m tall with a clear test opening 1.40 m wide and 2.40 m high. Both GLBs were imported back into Blender 4.3.2 to check geometry and scale. The meshes are static and await Unreal import, collision and gameplay calibration. The creature also needs a rig and animation.

The overlook has six shale plates, nine fern clusters and hanging roots. The GLB reimported into Blender 4.3.2 with 16 meshes. Thirty-five vertical rays confirmed a clear, level strip 3.00 m wide and 1.02 m deep on top. Unreal collision and connection to the authored terrain need a separate playtest.

The Branch Terraces ladder has eleven wooden rungs, an iron hinge and a suspended stone counterweight. The GLB reimported into Blender 4.3.2 with 43 meshes and three separate groups for the ladder, hoist and weight. The moving pivot is at the origin along Blender's local X axis. Check pivot conversion, collision and rope motion after Unreal import.

The 22-second stereo ambience uses original procedural root creaks, scattered drips and low wood resonance. To reproduce the 48 kHz PCM WAV and its manifest, pass an output directory to `python3 scripts/audio/render_buried_forest_ambience.py` from the repository root. Two independent renders produced identical WAVs.

The Fern Basin cues are mono 48 kHz PCM one-shots. The handwheel ends in a ratchet lock. The gate release folds into a short water churn. Both are original procedural syntheses. Regeneration from `python3 scripts/audio/render_fern_basin_cues.py <output>` matched both WAVs and their manifest byte for byte. In-game routing remains pending.

The Fern Basin handwheel is 0.688 m in diameter. Blender 4.3.2 reimported 57 meshes. A 90° rotation of the handwheel pivot moved the grip and left the hub center and fixed collar in place. Test materials, collision and linkage to the drain trigger in Unreal.
