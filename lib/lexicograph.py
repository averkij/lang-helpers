"""
Построитель двуязычных словарей из текстов с лейпцигской глоссировкой.

Модуль извлекает словарные пары (словоформа→глосса и морфема→глосса)
из глоссированных текстов и формирует словник и словарь морфем
с индексами цитирования.
"""

import json
import re
import string
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Lightweight internal data classes used when glossing_parser is unavailable
# ---------------------------------------------------------------------------

@dataclass
class Morpheme:
    """Морфема исходного языка и её глосса."""
    form: str
    gloss: str = ""


@dataclass
class Word:
    """Словоформа, состоящая из морфем."""
    form: str
    gloss: str = ""
    morphemes: List[Morpheme] = field(default_factory=list)


@dataclass
class Sentence:
    """Предложение из глоссированного текста."""
    id: str = ""
    original: str = ""
    segmented: str = ""
    glosses: str = ""
    translation: str = ""
    words: List[Word] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Punctuation handling
# ---------------------------------------------------------------------------

# Characters to strip from the edges of word forms and glosses
_PUNCT = set(string.punctuation + "«»—–…''""„‟‹›" + "。、，！？；：")


def _strip_punct(text: str) -> str:
    """Удаляет знаки препинания с краёв строки."""
    return text.strip().strip("".join(_PUNCT)).strip()


# ---------------------------------------------------------------------------
# Parser (standalone, used when glossing_parser is not available)
# ---------------------------------------------------------------------------

_SENT_NUM_RE = re.compile(r"^(\d+)\s*>")


def _parse_file_standalone(filepath: str) -> List[Sentence]:
    """
    Разбирает файл с лейпцигской глоссировкой.

    Формат: блоки из 4 строк, разделённые пустыми строками.
      <N>  нумерованная строка (оригинал)
      морфемно-сегментированная строка
      строка глосс
      'свободный перевод'
    """
    with open(filepath, "r", encoding="utf-8") as fh:
        raw = fh.read()

    sentences: List[Sentence] = []
    block: List[str] = []

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped:
            block.append(stripped)
        else:
            if block:
                sent = _block_to_sentence(block)
                if sent is not None:
                    sentences.append(sent)
                block = []
    # last block without trailing blank line
    if block:
        sent = _block_to_sentence(block)
        if sent is not None:
            sentences.append(sent)

    return sentences


def _block_to_sentence(block: List[str]) -> Optional[Sentence]:
    """Превращает блок строк в объект Sentence."""
    if len(block) < 3:
        return None

    # First line: numbered original
    first = block[0]
    m = _SENT_NUM_RE.match(first)
    if m:
        sent_id = m.group(1)
        original = _SENT_NUM_RE.sub("", first).strip()
    else:
        sent_id = ""
        original = first

    segmented = block[1]
    glosses = block[2]
    translation = block[3] if len(block) > 3 else ""

    # Strip surrounding quotes from translation
    translation = translation.strip().strip("'\"''""\u201c\u201d").strip()

    seg_tokens = segmented.split()
    gloss_tokens = glosses.split()

    words: List[Word] = []
    for i, seg_tok in enumerate(seg_tokens):
        gloss_tok = gloss_tokens[i] if i < len(gloss_tokens) else ""
        seg_parts = seg_tok.split("-")
        gloss_parts = gloss_tok.split("-") if gloss_tok else []

        morphemes: List[Morpheme] = []
        for j, sp in enumerate(seg_parts):
            gp = gloss_parts[j] if j < len(gloss_parts) else ""
            morphemes.append(Morpheme(form=sp, gloss=gp))

        words.append(Word(form=seg_tok, gloss=gloss_tok, morphemes=morphemes))

    return Sentence(
        id=sent_id,
        original=original,
        segmented=segmented,
        glosses=glosses,
        translation=translation,
        words=words,
    )


# ---------------------------------------------------------------------------
# Try to import the canonical parser; fall back to standalone
# ---------------------------------------------------------------------------

_use_glossing_parser = False
try:
    from lib.glossing_parser import (  # type: ignore
        parse_file as _gp_parse_file,
        Sentence as _GP_Sentence,
        Word as _GP_Word,
        Morpheme as _GP_Morpheme,
    )
    _use_glossing_parser = True
except ImportError:
    pass


def _parse_file(filepath: str) -> List[Sentence]:
    """Разбирает файл, используя glossing_parser если доступен."""
    if _use_glossing_parser:
        return _gp_parse_file(filepath)  # type: ignore[return-value]
    return _parse_file_standalone(filepath)


# ---------------------------------------------------------------------------
# Dictionary entry helpers
# ---------------------------------------------------------------------------

def _make_key(source: str, target: str) -> str:
    return f"{source}\t{target}"


def _add_entry(
    dictionary: dict,
    source: str,
    target: str,
    citation: str,
) -> None:
    """Добавляет запись в словарь (или сливает номер цитаты)."""
    source = _strip_punct(source)
    target = _strip_punct(target)
    if not source:
        return
    key = _make_key(source, target)
    if key not in dictionary:
        dictionary[key] = {"source": source, "target": target, "citations": []}
    if citation and citation not in dictionary[key]["citations"]:
        dictionary[key]["citations"].append(citation)


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_dictionaries_from_parsed(sentences: list) -> dict:
    """
    Строит словник и словарь морфем из списка объектов Sentence.

    Возвращает dict в формате JSON-структуры:
      {
        "word_dictionary": [...],
        "morpheme_dictionary": [...],
        "metadata": { ... }
      }
    """
    word_dict: dict = {}   # key -> entry
    morph_dict: dict = {}  # key -> entry

    total_words = 0
    total_morphemes = 0

    for sent in sentences:
        sid = str(getattr(sent, "id", ""))

        words = getattr(sent, "words", None)
        if words is None:
            continue

        for word in words:
            form = getattr(word, "form", "")
            gloss = getattr(word, "gloss", "") or ""

            # If no word-level gloss, reconstruct from morpheme glosses
            morphemes = getattr(word, "morphemes", None)
            if not gloss and morphemes:
                gloss_parts = [getattr(m, "gloss", "") for m in morphemes]
                gloss = "-".join(g for g in gloss_parts if g)

            clean_form = _strip_punct(form)
            if not clean_form:
                continue

            total_words += 1
            _add_entry(word_dict, clean_form, _strip_punct(gloss), sid)
            if morphemes:
                for morph in morphemes:
                    mform = _strip_punct(getattr(morph, "form", ""))
                    mgloss = _strip_punct(getattr(morph, "gloss", ""))
                    if mform:
                        total_morphemes += 1
                        _add_entry(morph_dict, mform, mgloss, sid)

    # Sort alphabetically by source form
    word_list = sorted(word_dict.values(), key=lambda e: e["source"].lower())
    morph_list = sorted(morph_dict.values(), key=lambda e: e["source"].lower())

    return {
        "word_dictionary": word_list,
        "morpheme_dictionary": morph_list,
        "metadata": {
            "total_words": total_words,
            "unique_words": len(word_list),
            "total_morphemes": total_morphemes,
            "unique_morphemes": len(morph_list),
        },
    }


def build_dictionaries(filepath: str) -> dict:
    """
    Основная функция: читает файл с глоссировкой и строит словари.

    Параметры:
        filepath: путь к файлу с лейпцигской глоссировкой.

    Возвращает dict с ключами word_dictionary, morpheme_dictionary, metadata.
    """
    sentences = _parse_file(filepath)
    return build_dictionaries_from_parsed(sentences)


# ---------------------------------------------------------------------------
# Output: JSON
# ---------------------------------------------------------------------------

def save_dictionary_json(data: dict, filepath: str) -> None:
    """Сохраняет словари в формате JSON."""
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Output: formatted text
# ---------------------------------------------------------------------------

def save_dictionary_text(data: dict, filepath: str) -> None:
    """
    Сохраняет словари в текстовом формате (словник).

    Формат:
        Словник
        <source>\t\t<target>\t\t<citations>
        ...

        Словарь морфем
        <source>\t\t<target>\t\t<citations>
    """
    lines: List[str] = []

    # Word-level dictionary
    lines.append("Словник")
    lines.append("")
    for entry in data.get("word_dictionary", []):
        cites = ", ".join(entry["citations"])
        lines.append(f"{entry['source']}\t\t{entry['target']}\t\t{cites}")

    lines.append("")
    lines.append("")

    # Morpheme-level dictionary
    lines.append("Словарь морфем")
    lines.append("")
    for entry in data.get("morpheme_dictionary", []):
        cites = ", ".join(entry["citations"])
        lines.append(f"{entry['source']}\t\t{entry['target']}\t\t{cites}")

    lines.append("")

    # Metadata summary
    meta = data.get("metadata", {})
    if meta:
        lines.append("")
        lines.append("Статистика")
        lines.append(f"  Всего словоформ: {meta.get('total_words', 0)}")
        lines.append(f"  Уникальных словоформ: {meta.get('unique_words', 0)}")
        lines.append(f"  Всего морфем: {meta.get('total_morphemes', 0)}")
        lines.append(f"  Уникальных морфем: {meta.get('unique_morphemes', 0)}")
        lines.append("")

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Построитель двуязычных словарей из глоссированных текстов"
    )
    parser.add_argument("input", help="Путь к файлу с лейпцигской глоссировкой")
    parser.add_argument(
        "-o", "--output",
        help="Путь для сохранения результата (без расширения)",
        default=None,
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "text", "both"],
        default="both",
        help="Формат вывода: json, text или both (по умолчанию: both)",
    )

    args = parser.parse_args()
    result = build_dictionaries(args.input)

    base = args.output or args.input.rsplit(".", 1)[0] + "_dict"

    if args.format in ("json", "both"):
        out_json = base + ".json"
        save_dictionary_json(result, out_json)
        print(f"JSON сохранён: {out_json}")

    if args.format in ("text", "both"):
        out_txt = base + ".txt"
        save_dictionary_text(result, out_txt)
        print(f"Словник сохранён: {out_txt}")

    meta = result["metadata"]
    print(f"\nСтатистика:")
    print(f"  Словоформ: {meta['total_words']} всего, {meta['unique_words']} уникальных")
    print(f"  Морфем: {meta['total_morphemes']} всего, {meta['unique_morphemes']} уникальных")
