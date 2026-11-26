# Catacombs prototypes

The Ossuary Tick is an original EIDOLON prototype for the Low-Arch Ossuary encounter. The Blender 4.3.2 round trip verified 54 mesh parts, 15,120 triangles, eight hooked legs, UVs, basic materials and bounds of approximately 78 × 79 × 43 cm. Rigging, collision fitting and Unreal import await verification.

- [Render](OssuaryTick.png)
- [GLB](OssuaryTick.glb)
- [Scrape telegraph WAV](sfx_ossuary_tick_scrape_telegraph.wav)
- [Audio manifest](manifest.json)

Regenerate the model using `blender -b -t 4 --python-exit-code 1 --python scripts/creatures/make_ossuary_tick.py -- /tmp/eidolon-ossuary-tick`. Regenerate the scrape using `python3 scripts/audio/render_ossuary_tick_telegraph.py /tmp/eidolon-ossuary-audio`.

The Lintel Mantis is an original static EIDOLON prototype for floor 3. The Blender 4.3.2 round trip verified 72 mesh parts, 13,060 triangles, two curved blades, wing membranes, UVs and basic materials, with bounds of about 156 × 136 × 189 cm.

- [Lintel Mantis render](LintelMantis.png)
- [Lintel Mantis GLB](LintelMantis.glb)
- [Blender generator](../../scripts/creatures/make_lintel_mantis.py)

The Censer Hagfish is an original static prototype for the Drainage Canals. A Blender 4.3.2 round trip verified 41 mesh parts, 27,312 triangles, UVs, materials and bounds of approximately 86 × 215 × 69 cm.

- [Censer Hagfish render](CenserHagfish.png)
- [Censer Hagfish GLB](CenserHagfish.glb)
- [Blender generator](../../scripts/creatures/make_censer_hagfish.py)

The Marrow Ram is a static EIDOLON prototype for the Broken Portico. The Blender 4.3.2 round trip verified 61 mesh parts, 32,460 triangles, UVs and basic materials. The bounding box is approximately 190 × 275 × 158 cm. The cranial wedge and hollow back are designed to read separately during its charge. Rigging and Unreal import are pending.

- [Marrow Ram render](MarrowRam.png)
- [Marrow Ram GLB](MarrowRam.glb)
- [Blender generator](../../scripts/creatures/make_marrow_ram.py)

The Ram windup has an original 1.0 second paired hoof scrape prototype. Two renders match byte for byte. The cue uses mono PCM16 at 48 kHz and awaits Unreal listening and timing review. [WAV](marrow-ram/sfx_marrow_ram_hoof_telegraph.wav) · [Manifest](marrow-ram/manifest.json)
