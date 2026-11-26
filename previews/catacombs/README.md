# Catacombs prototypes

The Ossuary Tick is an original EIDOLON prototype for the Low-Arch Ossuary encounter. The Blender 4.3.2 round trip verified 54 mesh parts, 15,120 triangles, eight hooked legs, UVs, basic materials and bounds of approximately 78 × 79 × 43 cm. Rigging, collision fitting and Unreal import await verification.

- [Render](OssuaryTick.png)
- [GLB](OssuaryTick.glb)
- [Scrape telegraph WAV](sfx_ossuary_tick_scrape_telegraph.wav)
- [Audio manifest](manifest.json)

Regenerate the model using `blender -b -t 4 --python-exit-code 1 --python scripts/creatures/make_ossuary_tick.py -- /tmp/eidolon-ossuary-tick`. Regenerate the scrape using `python3 scripts/audio/render_ossuary_tick_telegraph.py /tmp/eidolon-ossuary-audio`.
