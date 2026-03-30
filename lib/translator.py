"""
Конвертер глоссированных данных в JSON и CoNLL-U.

Принимает разобранные предложения и языковую схему, генерирует:
1. JSON-корпус с токенами, леммами, POS-тегами и признаками UD.
2. CoNLL-U формат (10 столбцов через табуляцию).
"""

import json
import logging
import re
from pathlib import Path
from types import ModuleType

from .glossing_parser import Sentence, Word

logger = logging.getLogger(__name__)

# Глоссы, указывающие на глагольную природу слова
_VERB_GLOSSES = frozenset({
    "IND", "CONV", "NMN", "ATR", "DES", "IMP", "COND", "HORT",
    "JUSS", "PROB", "PROH", "ISP", "SUBJ", "CAUS", "PROG", "ANT",
    "ITER", "USIT", "RES", "COMPL", "SIM", "AVERT", "HAB", "MULT",
    "FUT", "AUX", "NEG",
})

# Глоссы, типичные для существительных
_NOUN_GLOSSES = frozenset({
    "ABL", "PERL", "LOC", "DAT", "INST", "VOC", "CAUSEE", "COM",
    "COMP", "LIM", "REP", "SG", "DU", "PL", "POSS", "DIM", "CL",
    "INDEF", "ANY",
})

# Паттерн для распознавания числительных
_NUM_RE = re.compile(r'^[0-9]+$|^один$|^два$|^три$|^четыре$|^пять$|^шесть$|^семь$|^восемь$|^девять$|^десять$')


def _determine_pos(word: Word, scheme: ModuleType) -> str:
    """
    Определяет часть речи слова на основе его глосс и схемы.

    Логика:
    - Если лексическая глосса — числительное -> NUM
    - Если есть глагольные грамматические глоссы -> VERB
    - Если есть именные грамматические глоссы -> NOUN
    - Если глосса DISC -> INTJ
    - По умолчанию -> NOUN
    """
    grammatical_glosses = set()
    has_lexical = False

    for morpheme in word.morphemes:
        if morpheme.is_grammatical:
            # Разбираем слитные категории (напр. 3SG)
            gloss = morpheme.gloss
            grammatical_glosses.add(gloss)
        else:
            has_lexical = True
            # Проверяем, не числительное ли
            if _NUM_RE.match(morpheme.gloss):
                return "NUM"

    # Проверяем DISC -> INTJ
    if "DISC" in grammatical_glosses:
        return "INTJ"

    # Проверяем глагольные глоссы
    if grammatical_glosses & _VERB_GLOSSES:
        return "VERB"

    # Проверяем именные глоссы
    if grammatical_glosses & _NOUN_GLOSSES:
        return "NOUN"

    # По умолчанию
    return "NOUN"


def _get_features(word: Word, pos: str, scheme: ModuleType) -> list[str]:
    """
    Собирает признаки UD для слова на основе его глосс и схемы.
    Возвращает отсортированный список строк вида 'Feature=Value'.
    """
    morphdict = getattr(scheme, "morphdict", {})
    defaults_map = getattr(scheme, "defaults", {})

    features = []

    for morpheme in word.morphemes:
        if not morpheme.is_grammatical:
            continue

        gloss = morpheme.gloss

        # Сначала пробуем найти целую глоссу (напр. "3SG")
        if gloss in morphdict:
            value = morphdict[gloss]
            # Значение может содержать несколько признаков через |
            if value and not value.isupper():  # Не POS-тег типа "INTJ"
                for feat in value.split("|"):
                    if feat not in features:
                        features.append(feat)
            continue

        # Пробуем разбить слитные категории по точкам
        sub_glosses = gloss.split(".")
        for sg in sub_glosses:
            sg = sg.strip()
            if sg in morphdict:
                value = morphdict[sg]
                if value and not value.isupper():
                    for feat in value.split("|"):
                        if feat not in features:
                            features.append(feat)

    # Применяем дефолты из схемы
    if pos in defaults_map:
        pos_defaults = defaults_map[pos]
        for default_entry in pos_defaults:
            if isinstance(default_entry, tuple):
                # Условный дефолт: (условия, значение)
                conditions, default_value = default_entry
                if _check_conditions(conditions, features):
                    feat_name = default_value.split("=")[0]
                    if not any(f.startswith(feat_name + "=") for f in features):
                        features.append(default_value)
            elif isinstance(default_entry, str):
                # Безусловный дефолт
                feat_name = default_entry.split("=")[0]
                if not any(f.startswith(feat_name + "=") for f in features):
                    features.append(default_entry)

    features.sort()
    return features


def _check_conditions(conditions: list[str], current_features: list[str]) -> bool:
    """
    Проверяет, удовлетворяются ли условия для применения дефолта.

    Условия вида:
    - "Mood=Ind" — признак должен присутствовать
    - "Mood!=Imp" — признак НЕ должен присутствовать
    """
    for cond in conditions:
        if "!=" in cond:
            # Отрицательное условие
            feat_name, feat_val = cond.split("!=", 1)
            forbidden = f"{feat_name}={feat_val}"
            if forbidden in current_features:
                return False
        else:
            # Положительное условие
            if cond not in current_features:
                return False
    return True


def _word_to_token(word: Word, token_idx: int, pos: str, features: list[str]) -> dict:
    """Конвертирует Word в словарь токена для JSON."""
    lemma = word.lemma

    # Собираем глоссы
    gloss_parts = []
    for m in word.morphemes:
        if m.is_grammatical:
            gloss_parts.append(m.gloss)

    glosses_str = ".".join(gloss_parts) if gloss_parts else "_"

    tagsets = [features] if features else []

    return {
        "itoken": str(token_idx),
        "token": word.form,
        "lemma": lemma,
        "pos": pos,
        "tagsets": tagsets,
        "glosses": glosses_str,
    }


def translate_to_json(sentences: list[Sentence], scheme: ModuleType, source_name: str) -> dict:
    """
    Конвертирует список предложений в JSON-формат корпуса.

    Args:
        sentences: список разобранных предложений.
        scheme: модуль языковой схемы с morphdict, defaults и т.д.
        source_name: имя исходного файла.

    Returns:
        Словарь в формате JSON-корпуса.
    """
    language_code = getattr(scheme, "language_code", "und")

    json_sentences = []

    for sent in sentences:
        tokens = []
        for i, word in enumerate(sent.words):
            pos = _determine_pos(word, scheme)
            features = _get_features(word, pos, scheme)
            token = _word_to_token(word, i + 1, pos, features)
            tokens.append(token)

        json_sent = {
            "id": sent.id,
            "text": sent.original,
            "translation": sent.translation,
            "tokens": tokens,
        }
        json_sentences.append(json_sent)

    return {
        "sentences": json_sentences,
        "source": source_name,
        "language": language_code,
    }


def translate_to_conllu(sentences: list[Sentence], scheme: ModuleType) -> str:
    """
    Конвертирует список предложений в формат CoNLL-U.

    Формат: 10 столбцов через табуляцию:
    ID, FORM, LEMMA, UPOS, XPOS, FEATS, HEAD, DEPREL, DEPS, MISC

    Args:
        sentences: список разобранных предложений.
        scheme: модуль языковой схемы.

    Returns:
        Строка в формате CoNLL-U.
    """
    lines = []

    for sent in sentences:
        # Метаданные предложения
        lines.append(f"# sent_id = {sent.id}")
        lines.append(f"# text = {sent.original}")
        if sent.translation:
            lines.append(f"# translation = {sent.translation}")

        for i, word in enumerate(sent.words):
            token_id = str(i + 1)
            form = word.form
            lemma = word.lemma
            pos = _determine_pos(word, scheme)
            xpos = "_"
            features = _get_features(word, pos, scheme)
            feats_str = "|".join(features) if features else "_"
            head = "_"
            deprel = "_"
            deps = "_"
            misc = "_"

            cols = [token_id, form, lemma, pos, xpos, feats_str, head, deprel, deps, misc]
            lines.append("\t".join(cols))

        lines.append("")  # Пустая строка между предложениями

    return "\n".join(lines)


def save_json(data: dict, filepath: str) -> None:
    """
    Сохраняет данные в JSON-файл.

    Args:
        data: словарь для сериализации.
        filepath: путь к выходному файлу.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"JSON сохранён в {filepath}")


def save_conllu(text: str, filepath: str) -> None:
    """
    Сохраняет текст CoNLL-U в файл.

    Args:
        text: строка в формате CoNLL-U.
        filepath: путь к выходному файлу.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    logger.info(f"CoNLL-U сохранён в {filepath}")
