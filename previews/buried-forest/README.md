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
| Hollow Trunk pin and socket | [Render](hollow-trunk/hollow_trunk_pin.png) · [GLB](hollow-trunk/hollow_trunk_pin.glb) | [Blender generator](../../environment/build_hollow_trunk_pin.py) |
| Hollow Trunk pin cues | [Pickup](hollow-trunk/sfx_hollow_trunk_pin_pickup.wav) · [Seating](hollow-trunk/sfx_hollow_trunk_pin_seating.wav) · [Manifest](hollow-trunk/manifest.json) | [Audio generator](../../scripts/audio/render_hollow_trunk_cues.py) |
| Rootlet Canal gate and counterweight | [Render](rootlet-canal/rootlet_canal_gate.png) · [GLB](rootlet-canal/rootlet_canal_gate.glb) | [Blender generator](../../environment/build_rootlet_canal_gate.py) |
| Rootlet Canal release cue | [WAV](rootlet-canal/sfx_rootlet_canal_counterweight_gate.wav) · [Manifest](rootlet-canal/manifest.json) | [Audio generator](../../scripts/audio/render_rootlet_gate.py) |
| Suspended Trunks bridge | [Rest pose](suspended-trunks/suspended_trunks_bridge.png) · [Quarter-turn](suspended-trunks/suspended_trunks_bridge_turned.png) · [GLB](suspended-trunks/suspended_trunks_bridge.glb) | [Blender generator](../../environment/build_suspended_trunks_bridge.py) |
| Suspended bridge rotation cue | [WAV](suspended-trunks/sfx_suspended_bridge_rotation.wav) · [Manifest](suspended-trunks/manifest.json) | [Audio generator](../../scripts/audio/render_suspended_bridge.py) |
| Double Clearing latch | [First detent](double-clearing/double_clearing_latch.png) · [Second detent](double-clearing/double_clearing_latch_detent_b.png) · [GLB](double-clearing/double_clearing_latch.glb) | [Blender generator](../../environment/build_double_clearing_latch.py) |
| Double Clearing latch cues | [Catch](double-clearing/sfx_double_clearing_latch_held.wav) · [Opening](double-clearing/sfx_double_clearing_latch_open.wav) · [Manifest](double-clearing/manifest.json) | [Audio generator](../../scripts/audio/render_double_clearing_latch.py) |
| Vein Overlook balcony | [Render](vein-overlook/vein_overlook_balcony.png) · [GLB](vein-overlook/vein_overlook_balcony.glb) | [Blender generator](../../environment/build_vein_overlook_balcony.py) |
| Vein Overlook ambience | [WAV](vein-overlook/sfx_amb_vein_overlook.wav) · [Manifest](vein-overlook/manifest.json) | [Audio generator](../../scripts/audio/render_vein_overlook_ambience.py) |
| Riftroot Tangle | [Render](riftroot/riftroot_tangle.png) · [Raised wedge](riftroot/riftroot_tangle_wedge_raised.png) · [GLB](riftroot/riftroot_tangle.glb) | [Blender generator](../../scripts/creatures/make_riftroot_tangle.py) |
| Riftroot Tangle cues | [Rock wedge](riftroot/sfx_riftroot_rock_wedge.wav) · [Root draw](riftroot/sfx_riftroot_root_retraction.wav) · [Manifest](riftroot/manifest.json) | [Audio generator](../../scripts/audio/render_riftroot_cues.py) |

The Root Stalker stands approximately 2.94 m tall. Its layered bark, hooked limbs and exposed joint membranes are visible in the render. The arch is approximately 2.96 m wide and 4.14 m tall with a clear test opening 1.40 m wide and 2.40 m high. Both GLBs were imported back into Blender 4.3.2 to check geometry and scale. The meshes are static and await Unreal import, collision and gameplay calibration. The creature also needs a rig and animation.

The overlook has six shale plates, nine fern clusters and hanging roots. The GLB reimported into Blender 4.3.2 with 16 meshes. Thirty-five vertical rays confirmed a clear, level strip 3.00 m wide and 1.02 m deep on top. Unreal collision and connection to the authored terrain need a separate playtest.

The Branch Terraces ladder has eleven wooden rungs, an iron hinge and a suspended stone counterweight. The GLB reimported into Blender 4.3.2 with 43 meshes and three separate groups for the ladder, hoist and weight. The moving pivot is at the origin along Blender's local X axis. Check pivot conversion, collision and rope motion after Unreal import.

The 22-second stereo ambience uses original procedural root creaks, scattered drips and low wood resonance. To reproduce the 48 kHz PCM WAV and its manifest, pass an output directory to `python3 scripts/audio/render_buried_forest_ambience.py` from the repository root. Two independent renders produced identical WAVs.

The Fern Basin cues are mono 48 kHz PCM one-shots. The handwheel ends in a ratchet lock. The gate release folds into a short water churn. Both are original procedural syntheses. Regeneration from `python3 scripts/audio/render_fern_basin_cues.py <output>` matched both WAVs and their manifest byte for byte. In-game routing remains pending.

The Fern Basin handwheel is 0.688 m in diameter. Blender 4.3.2 reimported 57 meshes. A 90° rotation of the handwheel pivot moved the grip and left the hub center and fixed collar in place. Test materials, collision and linkage to the drain trigger in Unreal.

The Hollow Trunk pin has an independent transform along Blender's local −Y axis. The GLB shows the seated pose and the render shows the withdrawn pose. After Blender reimport, the pin cleared the socket at 30 sampled positions along 0.58 m of travel. The two original mono PCM16 cues cover pickup and seating. The GLB and cue imports and bindings are pending in Unreal.

The Rootlet Canal grate and stone weight are independent groups with opposite vertical travel. Blender 4.3.2 reimported 108 meshes. With the grate raised, 56 rays verified clearance in a 1.56 × 2.13 m central opening. The original 2.68-second release cue combines chain rattle, iron impact and room resonance. It regenerates to identical mono PCM16 at 48 kHz. Set up the gate, rope, collision and cue playback in Unreal.

The Suspended Trunks bridge has a centered Z pivot and a fixed stone islet. Blender verified 113 meshes, a clear 1.30 m prototype lane and clearance from the islet at 19 quarter-turn samples. This is a 5.39 m prop study. Widen and extend the bank spans to fit the authored floor before validating clearance in Unreal. The original 2.58-second rotation cue ends with a low latch seat and regenerates to identical mono PCM16 at 48 kHz.

The Double Clearing latch has independent handle and index tooth groups. Blender 4.3.2 reimported 43 valid meshes. Both seated detents and 38 sampled transit angles cleared the frame with the tooth retracted 7 cm. The first-detent catch and second-detent opening cues are original mono PCM16 at 48 kHz and regenerate byte for byte. Verify the pivot, animation and cue routing in Unreal.

Vein Overlook reimported as 37 valid meshes with a dry 3 m square tread confirmed by 169 sample rays. The original 21-second ambience is stereo PCM16 at 48 kHz. Independent renders matched byte for byte and seam samples remained within the take's typical changes.

Riftroot Tangle reimported with 59 meshes. The neutral form measures approximately 4.24 × 4.97 × 3.07 m, with independent limb and wedge pivots. Both original combat cues are mono PCM16 at 48 kHz and regenerate byte for byte. The meshes and audio await Unreal import, rigging and combat cue routing.
