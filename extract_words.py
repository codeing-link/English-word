#!/usr/bin/env python3
"""Extract English words and phrases from the primary/middle-school word lists."""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path


GRADE_RE = re.compile(r"(一|二|三|四|五|六|七|八|九)年级")
CHINESE_RE = re.compile(r"[\u3400-\u9fff]")
TABLE_SEPARATOR_RE = re.compile(r"^\s*:?-{3,}:?\s*$")
POS_RE = re.compile(
    r"\b(?:modal\s+v|n|v|adj|adv|prep|pron|conj|interj|det|num|abbr)\.?\b",
    re.IGNORECASE,
)


GRADE_ORDER = [
    "一年级",
    "二年级",
    "三年级",
    "四年级",
    "五年级",
    "六年级",
    "七年级",
    "八年级",
    "九年级",
]


def normalize_text(text: str) -> str:
    text = (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("…", "...")
        .replace("⋯⋯", "...")
        .replace("……", "...")
        .replace("\u00a0", " ")
    )
    ocr_corrections = {
        "ma\x1fer": "matter",
        "le\x1fer": "letter",
        "co\x1fon": "cotton",
        "bo\x1fom": "bottom",
        "bo\x1fle": "bottle",
        "so\x1f": "soft",
        "a\x1fend": "attend",
        "o\x1e": "off",
        "o\x1eer": "offer",
        "in\x1euence": "influence",
        "re\x1eect": "reflect",
        "\x1eoor": "floor",
        "li\x1d": "lift",
        "a\x1cord": "afford",
    }
    for bad, good in ocr_corrections.items():
        text = text.replace(bad, good)
    return text


def split_outside_parentheses(text: str, sep: str = ",") -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for idx, char in enumerate(text):
        if char in "（(":
            depth += 1
        elif char in "）)" and depth:
            depth -= 1
        elif char == sep and depth == 0:
            parts.append(text[start:idx])
            start = idx + 1
    parts.append(text[start:])
    return parts


def remove_parentheses(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\([^()]*\)", " ", text)
        text = re.sub(r"（[^（）]*）", " ", text)
    return text


def remove_phonetics(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        body = match.group(1).strip()
        if re.search(r"[ˈˌɑɒɔəɜʊʌɪʃʒθðŋæɛɡː@{}:]", body):
            return " "
        if re.search(r"[A-Z]", body):
            return " "
        if not re.search(r"\s", body):
            return " "
        return match.group(0)

    return re.sub(r"/([^/\n]+)/", replace, text)


def strip_markdown(text: str) -> str:
    text = re.sub(r"^\s*[-*+]\s*", "", text)
    text = re.sub(r"^\s*#+\s*", "", text)
    text = text.replace("**", "")
    return text.strip()


def clean_candidate(raw: str) -> str | None:
    text = normalize_text(raw)
    text = strip_markdown(text)
    text = text.strip(" \t|")

    if not text:
        return None

    text = re.sub(r"^\*+", "", text).strip()
    text = re.sub(r"\bp\.\s*\d+\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\(\s*\d+\s*\)", " ", text)
    text = re.sub(r"^([A-Za-z]+)\s+\(=.*", r"\1", text)
    text = re.sub(r"\(=[^)]*\)", " ", text)
    text = re.sub(r"[（(][^）)]*[\u3400-\u9fff][^）)]*[）)]", " ", text)
    text = re.sub(r"\s*/[^/\n]*[ˈˌɑɒɔəɜʊʌɪʃʒθðŋæɛɡː@{}:][^/\n]*$", " ", text)
    text = re.sub(r"\([^()\n]*$", " ", text)

    chinese_match = CHINESE_RE.search(text)
    if chinese_match:
        text = text[: chinese_match.start()]

    text = remove_phonetics(text)
    text = remove_parentheses(text)

    pos_match = POS_RE.search(text)
    if pos_match:
        text = text[: pos_match.start()]

    text = re.sub(r"\bpl\.\s*\w+\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+,\s+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(" .,:;!?，。；：！？、()（）[]【】《》\"")

    if not text or not re.search(r"[A-Za-z]", text):
        return None
    if re.fullmatch(r"(starter\s+)?unit\s+\d+", text, flags=re.IGNORECASE):
        return None
    if text.lower() in {"page", "word", "words"}:
        return None

    return text


def is_grade_heading(line: str) -> bool:
    return bool(detect_grade(line))


def is_unit_heading(line: str) -> bool:
    return bool(re.fullmatch(r"\s*(?:#{1,6}\s*)?(?:Starter\s+)?Unit\s+\d+\s*\d*\s*", line, re.IGNORECASE))


def is_middle_continuation(line: str) -> bool:
    stripped = normalize_text(line).strip()
    if not stripped:
        return False
    if stripped.startswith("#") or is_grade_heading(stripped) or is_unit_heading(stripped):
        return False
    if CHINESE_RE.match(stripped):
        return True
    if stripped.startswith("/") or re.match(r"^[ˈˌɑɒɔəɜʊʌɪʃʒθðŋæɛɡː@{}]", stripped):
        return True
    if re.match(r"^(?:n|v|adj|adv|prep|pron|conj|interj|modal\b|&)\.?\b", stripped, re.IGNORECASE):
        return True
    if re.match(r"^(?:and|or)\b", stripped, re.IGNORECASE) and not CHINESE_RE.search(stripped):
        return True
    return False


def is_capitalized_name_tail(line: str) -> bool:
    stripped = normalize_text(line).strip()
    return bool(re.match(r"^[A-Z][A-Za-z-]+(?:\s+[\u3400-\u9fff]|$)", stripped))


def iter_source_lines(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").split("\n")
    if "中学" not in path.name:
        return lines

    merged: list[str] = []
    buffer = ""

    for raw_line in lines:
        line = normalize_text(raw_line).rstrip()
        if not line.strip():
            if buffer:
                merged.append(buffer)
                buffer = ""
            merged.append(line)
            continue

        if is_grade_heading(line) or is_unit_heading(line) or line.lstrip().startswith("#"):
            if buffer:
                merged.append(buffer)
                buffer = ""
            merged.append(line)
            continue

        if buffer and (
            is_middle_continuation(line)
            or buffer.count("(") > buffer.count(")")
            or (not CHINESE_RE.search(buffer) and is_capitalized_name_tail(line))
        ):
            buffer = f"{buffer} {line.strip()}"
            continue

        if buffer:
            merged.append(buffer)
        buffer = line

    if buffer:
        merged.append(buffer)

    return merged


def extract_line_candidates(line: str) -> list[str]:
    normalized = normalize_text(line).strip()
    if not normalized or normalized == "---":
        return []

    if re.match(r"^\s*#{1,6}\s*", normalized):
        return []

    unit_inline = re.match(r"^\s*[-*+]\s+\*\*Unit\s+\d+\*\*\s*:\s*(.+)$", normalized, re.IGNORECASE)
    if unit_inline:
        return [part for part in split_outside_parentheses(unit_inline.group(1)) if part.strip()]

    if normalized.startswith("|") and normalized.endswith("|"):
        cells = [cell.strip() for cell in normalized.strip("|").split("|")]
        if not cells or TABLE_SEPARATOR_RE.match(cells[0]):
            return []
        first_cell = cells[0]
        if first_cell.lower() in {"english", "单词 / 短语", "单词", "word"}:
            return []
        return [first_cell]

    bold_items = re.findall(r"\*\*([^*]+)\*\*", normalized)
    bold_items = [item for item in bold_items if not re.fullmatch(r"Unit\s+\d+", item, flags=re.IGNORECASE)]
    if bold_items:
        return bold_items

    if re.fullmatch(r"(Starter\s+)?Unit\s+\d+\s*\d*", normalized, flags=re.IGNORECASE):
        return []

    return [normalized]


def detect_grade(line: str) -> str | None:
    match = GRADE_RE.search(line)
    if not match:
        return None
    return f"{match.group(1)}年级"


def extract_from_file(path: Path, words_by_grade: OrderedDict[str, list[str]]) -> None:
    current_grade: str | None = None

    for line in iter_source_lines(path):
        grade = detect_grade(line)
        if grade:
            current_grade = grade
            words_by_grade.setdefault(current_grade, [])
            continue

        if not current_grade:
            continue

        for raw_candidate in extract_line_candidates(line):
            candidate = clean_candidate(raw_candidate)
            if candidate:
                words_by_grade[current_grade].append(candidate)


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def write_outputs(words_by_grade: OrderedDict[str, list[str]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ordered = OrderedDict()
    for grade in GRADE_ORDER:
        if grade in words_by_grade:
            ordered[grade] = dedupe_preserve_order(words_by_grade[grade])

    (output_dir / "words_by_grade.json").write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for grade, words in ordered.items():
        (output_dir / f"{grade}.txt").write_text("\n".join(words) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        default=[Path("1英语单词-小学.md"), Path("2英语单词-中学.md")],
        help="Markdown files to parse. Defaults to the two word-list files in this directory.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for words_by_grade.json and per-grade txt files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    words_by_grade: OrderedDict[str, list[str]] = OrderedDict()

    for file_path in args.files:
        if not file_path.exists():
            raise FileNotFoundError(file_path)
        extract_from_file(file_path, words_by_grade)

    write_outputs(words_by_grade, args.output_dir)

    for grade in GRADE_ORDER:
        if grade in words_by_grade:
            count = len(dedupe_preserve_order(words_by_grade[grade]))
            print(f"{grade}: {count} words/phrases")
    print(f"Output written to: {args.output_dir}")


if __name__ == "__main__":
    main()
