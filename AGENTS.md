# EIDOLON tools

- Base work on `integration/studio`, preserve existing branches, and keep `main` intact. Read `docs/STUDIO-INTEGRATION.md` and the ownership, dependencies and release criteria in `eidolon-docs/production/`.
- Coordinate changes to shared schemas and build entry points with their owners. Keep departments' changes isolated and compare PR ancestry before importing work.
- Run `python3 scripts/validate_project.py /path/to/eidolon-game` for the shared layout check. For changes to asset tools, verify the generated output, provenance and license. Record Blender execution, Unreal import and visual review separately when required.
- Use authorized toolchains and assets. Preserve signature and checksum verification. Keep secrets, engine distributions and console SDKs outside Git.
- Follow `eidolon-docs/art/asset-fidelity-review.md` when authoring or revising 3D art. Review the exported GLB with its embedded maps and close-up lighting, and verify scale and moving pivots where applicable.
- Add department handoffs in `docs/handoff/NN.md` with the commit, commands and observed results.
