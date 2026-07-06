#!/usr/bin/env python3
"""Split each grade file in src into separate word and phrase files."""

from __future__ import annotations

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


def split_grade_file(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8").rstrip("\n")
    parts = text.split("\n\n", 1)
    words = parts[0].splitlines() if parts and parts[0] else []
    phrases = parts[1].splitlines() if len(parts) > 1 and parts[1] else []
    return words, phrases


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main() -> None:
    src_dir = Path("src")
    words_dir = Path("output/words")
    phrases_dir = Path("output/phrases")
    words_dir.mkdir(parents=True, exist_ok=True)
    phrases_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        src_dir.glob("*.txt"),
        key=lambda path: (GRADE_ORDER.get(path.name, 999), path.name),
    )

    for src_file in files:
        words, phrases = split_grade_file(src_file)
        write_lines(words_dir / src_file.name, words)
        write_lines(phrases_dir / src_file.name, phrases)
        print(f"{src_file.name}: {len(words)} words, {len(phrases)} phrases")


if __name__ == "__main__":
    main()
