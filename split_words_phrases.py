#!/usr/bin/env python3
"""Split each grade word list into words first and phrases second."""

from __future__ import annotations

import argparse
from pathlib import Path


GRADE_ORDER = {
    "一年级.txt": 1,
    "二年级.txt": 2,
    "三年级.txt": 3,
    "四年级.txt": 4,
    "五年级.txt": 5,
    "六年级.txt": 6,
    "七年级.txt": 7,
    "八年级.txt": 8,
    "九年级.txt": 9,
}


def is_phrase(entry: str) -> bool:
    """Return True for multi-word expressions and sentence-like entries."""
    return any(marker in entry for marker in (" ", "\t", "=", "/", "..."))


def read_entries(path: Path) -> list[str]:
    entries: list[str] = []
    seen: set[str] = set()

    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if not entry:
            continue
        key = entry.casefold()
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)

    return entries


def split_entries(entries: list[str]) -> tuple[list[str], list[str]]:
    words: list[str] = []
    phrases: list[str] = []

    for entry in entries:
        if is_phrase(entry):
            phrases.append(entry)
        else:
            words.append(entry)

    return words, phrases


def write_split_file(output_path: Path, words: list[str], phrases: list[str]) -> None:
    content = "\n".join(words)
    content += "\n\n"
    content += "\n".join(phrases)
    content += "\n"
    output_path.write_text(content, encoding="utf-8")


def source_files(src_dir: Path) -> list[Path]:
    files = [path for path in src_dir.glob("*.txt") if path.is_file()]
    return sorted(files, key=lambda path: (GRADE_ORDER.get(path.name, 999), path.name))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src-dir", type=Path, default=Path("src"), help="Directory containing grade txt files.")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="Directory for split txt files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for input_path in source_files(args.src_dir):
        entries = read_entries(input_path)
        words, phrases = split_entries(entries)
        write_split_file(args.output_dir / input_path.name, words, phrases)
        print(f"{input_path.name}: {len(words)} words, {len(phrases)} phrases")


if __name__ == "__main__":
    main()
