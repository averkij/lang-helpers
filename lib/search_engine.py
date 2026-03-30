"""
Поисковый движок по корпусу.

Осуществляет поиск по грамматическим признакам в JSON-корпусе,
подготовленном модулем перевода. Поддерживает фильтрацию по словоформе,
лемме, части речи и морфологическим признакам.
"""

import json
import os
from typing import Any


def load_corpus(filepath: str) -> dict:
    """
    Загружает корпус из JSON-файла.

    Args:
        filepath: путь к JSON-файлу корпуса.

    Returns:
        Словарь с данными корпуса.

    Raises:
        FileNotFoundError: если файл не найден.
        json.JSONDecodeError: если файл содержит невалидный JSON.
    """
    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Файл корпуса не найден: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_feature(feature_str: str) -> tuple[str, str] | None:
    """
    Разбирает строку признака вида "Case=Abl" на пару (категория, значение).

    Args:
        feature_str: строка вида "Category=Value".

    Returns:
        Кортеж (категория, значение) или None, если формат неверный.
    """
    if "=" not in feature_str:
        return None
    cat, val = feature_str.split("=", 1)
    return (cat, val)


def _token_has_features(token: dict, features: dict[str, list[str]]) -> bool:
    """
    Проверяет, содержит ли токен указанные грамматические признаки.

    Логика:
    - Значения внутри одной категории объединяются через ИЛИ.
    - Разные категории объединяются через И.
    - Токен считается совпавшим, если хотя бы один из его наборов тегов
      удовлетворяет всем условиям.

    Args:
        token: словарь токена из корпуса.
        features: словарь категория -> список допустимых значений.

    Returns:
        True, если токен соответствует всем условиям.
    """
    tagsets = token.get("tagsets", [])
    if not tagsets:
        return False

    for tagset in tagsets:
        # Разбираем теги в набор пар (категория, значение)
        parsed: dict[str, set[str]] = {}
        for tag in tagset:
            pair = _parse_feature(tag)
            if pair:
                cat, val = pair
                if cat not in parsed:
                    parsed[cat] = set()
                parsed[cat].add(val)

        # Проверяем, что все требуемые категории представлены
        all_match = True
        for req_cat, req_vals in features.items():
            token_vals = parsed.get(req_cat, set())
            # ИЛИ внутри категории: хотя бы одно значение должно совпасть
            if not token_vals.intersection(req_vals):
                all_match = False
                break

        if all_match:
            return True

    return False


def _token_has_additional(token: dict, additional: list[str]) -> bool:
    """
    Проверяет наличие дополнительных признаков (вида "Feature=Value") в токене.

    Все указанные признаки должны присутствовать (логическое И).

    Args:
        token: словарь токена из корпуса.
        additional: список строк вида "Feature=Value".

    Returns:
        True, если все указанные признаки найдены хотя бы в одном наборе тегов.
    """
    tagsets = token.get("tagsets", [])
    if not tagsets:
        return False

    for tagset in tagsets:
        tag_set = set(tagset)
        if all(feat in tag_set for feat in additional):
            return True

    return False


def _match_token(token: dict, query: dict) -> bool:
    """
    Проверяет, соответствует ли токен поисковому запросу.

    Args:
        token: словарь токена из корпуса.
        query: словарь поискового запроса.

    Returns:
        True, если токен соответствует всем условиям запроса.
    """
    search_type = query.get("search_type", "token")

    # Проверка словоформы (подстрока)
    wordform = query.get("wordform")
    if wordform is not None:
        target = token.get("token", "") if search_type == "token" else token.get("lemma", "")
        if wordform.lower() not in target.lower():
            return False

    # Проверка леммы (подстрока)
    lemma = query.get("lemma")
    if lemma is not None:
        if lemma.lower() not in token.get("lemma", "").lower():
            return False

    # Проверка части речи
    pos_list = query.get("pos")
    if pos_list is not None:
        if token.get("pos", "") not in pos_list:
            return False

    # Проверка грамматических признаков
    features = query.get("features")
    if features:
        if not _token_has_features(token, features):
            return False

    # Проверка дополнительных признаков
    additional = query.get("additional")
    if additional:
        if not _token_has_additional(token, additional):
            return False

    return True


def _extract_token_features(token: dict) -> list[str]:
    """
    Извлекает все уникальные признаки из всех наборов тегов токена.

    Args:
        token: словарь токена из корпуса.

    Returns:
        Список строк признаков.
    """
    features = []
    seen = set()
    for tagset in token.get("tagsets", []):
        for tag in tagset:
            if tag not in seen:
                features.append(tag)
                seen.add(tag)
    return features


def search_corpus(corpus: dict, query: dict) -> dict:
    """
    Выполняет поиск по корпусу согласно заданному запросу.

    Возвращает все предложения, содержащие хотя бы один токен,
    соответствующий условиям запроса. Совпавшие токены выделяются
    в результатах.

    Args:
        corpus: словарь корпуса с ключом "sentences".
        query: словарь поискового запроса. Поддерживаемые ключи:
            - "wordform": подстрока для поиска по словоформе.
            - "lemma": подстрока для поиска по лемме.
            - "pos": список частей речи (ИЛИ).
            - "features": словарь категория -> список значений.
            - "additional": список дополнительных признаков.
            - "search_type": "token" или "lemma".

    Returns:
        Словарь с результатами:
            - "total": количество найденных предложений.
            - "results": список совпавших предложений с выделенными токенами.
    """
    sentences = corpus.get("sentences", [])
    results = []

    for sentence in sentences:
        tokens = sentence.get("tokens", [])
        matched_tokens = []

        for token in tokens:
            if _match_token(token, query):
                matched_tokens.append({
                    "itoken": token.get("itoken", ""),
                    "token": token.get("token", ""),
                    "pos": token.get("pos", ""),
                    "features": _extract_token_features(token),
                })

        if matched_tokens:
            results.append({
                "id": sentence.get("id", ""),
                "text": sentence.get("text", ""),
                "translation": sentence.get("translation", ""),
                "matched_tokens": matched_tokens,
            })

    return {
        "total": len(results),
        "results": results,
    }
