# Lost Mines previews

## Mine Borer

The floor-21 creature has a low digging wedge, broad forelimbs and articulated rear armor panels. Iron-rich shale and layered chitin use original embedded base color, normal and roughness maps. The hinged rear plates reveal ochre cuticle during the recovery pose. [Four-view sheet](mine-borer/perforatore.png) · [Whole model](mine-borer/front.png) · [Head and digging claws](mine-borer/front_detail.png) · [Rear plates closed](mine-borer/rear_closed.png) · [Rear plates lifted](mine-borer/rear_open.png) · [GLB](mine-borer/MineBorer.glb) · [Verification](mine-borer/verification.json)

Blender 4.3.2 reimported the 3.01 m model, its nine pivots and maps. From the matched rear view, 145 of 472 cuticle samples were visible with the plates closed and 247 were visible during recovery. Skeletal deformation, hit zones, animation, in-game material response and LODs remain to be tested in Unreal Engine 5.6.

The Unreal source export splits the GLB into the body, head and two rear plates, with a pivot origin for each piece. Blender reimported all four files. The maximum sampled vertex error in the assembled recovery pose was 0.000642 mm. [Reassembled rest pose](mine-borer/assembled_front.png) · [Reassembled recovery pose](mine-borer/assembled_recovery.png)

```sh
blender -b -t 4 --python-exit-code 1 -P scripts/creatures/make_mine_borer.py -- /path/to/output
blender -b -t 4 --python-exit-code 1 -P scripts/creatures/export_mine_borer_parts.py -- /path/to/assembly --samples 24
```

## Audio

The Mine Borer charge study for Abyss floor 21 combines a jaw strike, a sustained scrape and falling grit. The original audio was synthesized in the project at 48 kHz, mono PCM16. Two independent renders produced identical WAVs and manifests. [WAV](mine-borer/sfx_mine_borer_charge.wav) · [Timing and checksum](mine-borer/manifest.json) · [Generator](../../scripts/audio/render_mine_borer_charge.py)

The game uses three cues from the same design. The jaw strikes as the head drops, the scrape follows the Borer through the charge, and debris starts at contact. The charge channel fades over 70 ms at impact so the scrape can stop early. The 2.63-second preview demonstrates an early stop with the authored tracks. [Early-stop preview](mine-borer/audio/borer_short_charge_preview.wav) · [Phase WAVs and checksums](mine-borer/audio/manifest.json)

Regenerate the cues with `python3 -B scripts/audio/render_mine_borer_charge.py /path/to/audio --gameplay`. The WAVs and manifest matched across two runs. Verify playback, falloff, occlusion and the early stop in Unreal Engine 5.6.
