# First Descent asset previews

Original EIDOLON production prototypes. Source generators are in this repository. Blender 4.3.2 generated both meshes and successfully reimported their GLB exports. Rigging, collision, socket fitting, gameplay integration and Unreal import are pending. Blender render materials can include procedural details absent from the GLB.

| Asset | Preview | Output | Verification |
| --- | --- | --- | --- |
| Catacomb Crawler | [Render](CatacombCrawler.png) | [GLB](CatacombCrawler.glb) | Six limbs, two mandibles, UVs and materials. 27,420 triangles, 2.04 m tall. |
| Valdris recruit sword | [Render](valdris_recruit_sword.png) | [GLB](valdris_recruit_sword.glb) | 17 mesh parts, 1.022 m long. |
| Abyss floor 01 ambience | [12-second loop](sfx_amb_abyss_floor_01.wav) | [Audio manifest](manifest.json) | Repeat renders match byte for byte. Stereo PCM16 at 48 kHz. In-game mix pending. |

From the Tools repository, regenerate into an output directory:

```bash
blender -b --factory-startup --python scripts/creatures/make_catacomb_crawler.py -- /tmp/eidolon-crawler
blender -b --factory-startup --python equipment/build_valdris_sword.py -- /tmp/eidolon-sword
python3 scripts/audio/render_abyss_floor01.py /tmp/eidolon-audio
```
