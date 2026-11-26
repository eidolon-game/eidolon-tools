# Buried Forest Threshold previews

| Asset | Preview | Authoring source |
| --- | --- | --- |
| Root Stalker | [Render](RootStalker.png) · [GLB](RootStalker.glb) | [Blender generator](../../scripts/creatures/make_root_stalker.py) |
| Root Arch | [Render](buried_forest_root_arch.png) · [GLB](buried_forest_root_arch.glb) | [Blender generator](../../environment/build_buried_forest_arch.py) |
| Buried Forest ambience | [WAV](ambience/sfx_amb_buried_forest.wav) · [Manifest](ambience/manifest.json) | [Audio generator](../../scripts/audio/render_buried_forest_ambience.py) |

The Root Stalker stands approximately 2.94 m tall. Its layered bark, hooked limbs and exposed joint membranes are visible in the render. The arch is approximately 2.96 m wide and 4.14 m tall with a clear test opening 1.40 m wide and 2.40 m high. Both GLBs were imported back into Blender 4.3.2 to check geometry and scale. The meshes are static and await Unreal import, collision and gameplay calibration. The creature also needs a rig and animation.

The 22-second stereo ambience uses original procedural root creaks, scattered drips and low wood resonance. To reproduce the 48 kHz PCM WAV and its manifest, pass an output directory to `python3 scripts/audio/render_buried_forest_ambience.py` from the repository root. Two independent renders produced identical WAVs.
