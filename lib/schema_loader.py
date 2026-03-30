"""
Загрузчик схем языков.

Загружает конфигурационные файлы языковых схем из директории schemas/.
Каждая схема описывает морфологическую систему языка: словарь глосс,
значения по умолчанию, метаданные и т.д.
"""

import importlib.util
import os
from dataclasses import dataclass, field
from typing import Any


SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas")


@dataclass
class LanguageScheme:
    """Схема языка, содержащая морфологическую конфигурацию."""

    morphdict: dict[str, str]
    defaults: dict[str, list]
    prefixes: bool
    adjectives: bool
    language_name: str
    language_name_en: str
    language_code: str
    categories: dict[str, list[str]] = field(default_factory=dict)
    additional_features: list[str] = field(default_factory=list)


def get_categories(morphdict: dict[str, str]) -> dict[str, list[str]]:
    """
    Извлекает группировку признаков по категориям из морфологического словаря.

    Из записей вида "ABL": "Case=Abl" строит словарь:
        {"Case": ["Abl", "Per", "Loc", ...], "Number": ["Sing", "Dual", "Plur"], ...}

    Составные значения (содержащие '|') раскладываются на отдельные пары.
    Записи вида "X=Yes" (булевые признаки) и записи без '=' пропускаются.

    Args:
        morphdict: словарь глосс -> значения Universal Dependencies.

    Returns:
        Словарь категория -> список значений.
    """
    categories: dict[str, list[str]] = {}

    for value in morphdict.values():
        # Разбираем составные значения вроде "Person=3|Number=Sing"
        parts = value.split("|")
        for part in parts:
            if "=" not in part:
                continue
            cat, val = part.split("=", 1)
            if val == "Yes":
                # Булевые признаки обрабатываются отдельно
                continue
            if cat not in categories:
                categories[cat] = []
            if val not in categories[cat]:
                categories[cat].append(val)

    return categories


def _get_additional_features(morphdict: dict[str, str]) -> list[str]:
    """
    Извлекает список булевых признаков (вида "X=Yes") из морфологического словаря.

    Args:
        morphdict: словарь глосс -> значения Universal Dependencies.

    Returns:
        Список строк вида "Feature=Yes".
    """
    additional: list[str] = []

    for value in morphdict.values():
        parts = value.split("|")
        for part in parts:
            if "=" not in part:
                continue
            _, val = part.split("=", 1)
            if val == "Yes" and part not in additional:
                additional.append(part)

    return additional


def load_scheme(filepath: str) -> LanguageScheme:
    """
    Загружает языковую схему из Python-файла.

    Args:
        filepath: путь к .py файлу схемы.

    Returns:
        Объект LanguageScheme с загруженными данными.

    Raises:
        FileNotFoundError: если файл не найден.
        AttributeError: если в файле отсутствуют обязательные атрибуты.
    """
    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Файл схемы не найден: {filepath}")

    module_name = os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    morphdict = getattr(module, "morphdict", None)
    if morphdict is None:
        raise AttributeError(f"В файле схемы отсутствует обязательный атрибут 'morphdict': {filepath}")

    defaults = getattr(module, "defaults", {})
    prefixes = getattr(module, "prefixes", False)
    adjectives = getattr(module, "adjectives", False)
    language_name = getattr(module, "language_name", module_name)
    language_name_en = getattr(module, "language_name_en", module_name)
    language_code = getattr(module, "language_code", "")

    categories = get_categories(morphdict)
    additional_features = _get_additional_features(morphdict)

    return LanguageScheme(
        morphdict=morphdict,
        defaults=defaults,
        prefixes=prefixes,
        adjectives=adjectives,
        language_name=language_name,
        language_name_en=language_name_en,
        language_code=language_code,
        categories=categories,
        additional_features=additional_features,
    )


def load_scheme_by_name(name: str) -> LanguageScheme:
    """
    Загружает языковую схему по имени из директории schemas/.

    Args:
        name: имя схемы (без расширения .py).

    Returns:
        Объект LanguageScheme.

    Raises:
        FileNotFoundError: если схема с таким именем не найдена.
    """
    filepath = os.path.join(SCHEMAS_DIR, f"{name}.py")
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Схема '{name}' не найдена в директории: {SCHEMAS_DIR}")
    return load_scheme(filepath)


def list_available_schemes() -> list[str]:
    """
    Возвращает список имён доступных схем в директории schemas/.

    Returns:
        Список имён схем (без расширения .py).
    """
    if not os.path.isdir(SCHEMAS_DIR):
        return []

    schemes = []
    for filename in sorted(os.listdir(SCHEMAS_DIR)):
        if filename.endswith(".py") and not filename.startswith("_") and "TEMPLATE" not in filename.upper():
            schemes.append(filename[:-3])
    return schemes
