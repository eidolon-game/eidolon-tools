"""Structural data checks; not Unreal compilation."""
import csv
import json
import subprocess
from pathlib import Path

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def invalid_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")

def validate(path):
    if path.suffix.lower() in {".json", ".uproject", ".uplugin"}:
        json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_pairs,
                   parse_constant=invalid_constant)
    elif path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = csv.reader(stream, strict=True)
            header = next(rows, [])
            if not header or any(not field.strip() for field in header) or len(set(header)) != len(header):
                raise ValueError("invalid CSV header")
            for row in rows:
                if len(row) != len(header):
                    raise ValueError(f"CSV width mismatch at line {rows.line_num}")

def main():
    root = Path(__file__).resolve().parents[2]
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode("utf-8").split("\0")
    errors = []
    count = 0
    for name in tracked:
        path = root / name
        if path.suffix.lower() not in {".json", ".uproject", ".uplugin", ".csv"}:
            continue
        count += 1
        try:
            validate(path)
        except (ValueError, OSError, csv.Error) as exc:
            errors.append(f"{name}: {exc}")
    print(f"Structural data validation: {count} files, {len(errors)} errors")
    for error in errors:
        print(error)
    return int(bool(errors))

if __name__ == "__main__":
    raise SystemExit(main())
