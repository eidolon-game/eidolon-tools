# EIDOLON Tools

Development and validation utilities for EIDOLON. Python 3 standard library preferred; no secrets or licensed third-party assets in this public repository.

Status: bootstrap v0.0.1.

## Cloud development

Run the source checks from a directory containing the studio checkouts:

```bash
./eidolon-tools/scripts/init-cloud.sh
```

Set `EIDOLON_GAME_ROOT` to use a game checkout outside that directory. The command
checks Git, Git LFS and Python and runs the tools and game source validators.

Use `--with-cmake` on x86-64 Linux to install CMake 3.31.10 from a hash-locked
PyPI wheel into an isolated environment. For later commands, use
`/workspace/.eidolon-cloud/cmake-3.31.10/bin/cmake`, or set
`EIDOLON_CLOUD_DIR` to choose a different installation directory.

With an authorized Unreal Engine 5.6 Linux installation, set `UE_ROOT` to
the directory containing `Engine` and use `--require-ue`. This checks the
engine version, the editor executable and the UBT/UAT commands. Editor
compilation, packaging and playtests are separate release gates.
