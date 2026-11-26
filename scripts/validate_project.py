#!/usr/bin/env python3
"""Validate the minimal EIDOLON Unreal source layout."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    root = args.root
    required = ['Eidolon.uproject', 'Source/Eidolon/Eidolon.Build.cs', 'Source/Eidolon/Eidolon.cpp', 'Source/Eidolon.Target.cs', 'Source/EidolonEditor.Target.cs', '.gitattributes']
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        parser.exit(1, 'Missing: ' + ', '.join(missing) + '\n')
    project = json.loads((root / 'Eidolon.uproject').read_text(encoding='utf-8'))
    if not any(m.get('Name') == 'Eidolon' for m in project.get('Modules', [])):
        parser.exit(1, 'Missing Eidolon runtime module\n')
    print('Source layout OK (not a build test)')


if __name__ == '__main__':
    main()
