"""
API-эндпоинты поиска по корпусу.

Принимает поисковый запрос в формате JSON,
возвращает найденные предложения с подсвеченными совпадениями.
"""

import logging
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"


class SearchQuery(BaseModel):
    """Модель поискового запроса."""
    language: str = ""
    query: str = ""
    search_mode: str = "token"  # "token" или "lemma"
    pos: Any = Field(default_factory=list)
    features: Any = Field(default_factory=dict)
    additional: Any = Field(default_factory=list)


def _normalize_to_str_list(value: Any) -> list[str]:
    """Приводит одиночное значение/список к list[str]."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v is not None and str(v) != ""]
    if isinstance(value, str):
        return [value] if value else []
    return [str(value)]


def _normalize_features(value: Any) -> dict[str, list[str]]:
    """Нормализует признаки в формат {категория: [значения]}."""
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, list[str]] = {}
    for key, raw_val in value.items():
        if key is None:
            continue
        key_str = str(key)
        values = _normalize_to_str_list(raw_val)
        if values:
            normalized[key_str] = values
    return normalized


def _language_aliases(language: str) -> set[str]:
    aliases = {language} if language else set()
    if not language:
        return aliases

    try:
        from lib.schema_loader import list_available_schemes, load_scheme_by_name
    except ImportError:
        return aliases

    try:
        scheme_names = list_available_schemes()
    except Exception:
        return aliases

    for scheme_name in scheme_names:
        try:
            scheme = load_scheme_by_name(scheme_name)
        except Exception:
            continue

        scheme_code = getattr(scheme, "language_code", "")
        if language in {scheme_name, scheme_code}:
            aliases.add(scheme_name)
            if scheme_code:
                aliases.add(scheme_code)

    return aliases


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _flat_corpus_matches_language(filepath: Path, aliases: set[str]) -> bool:
    if any(filepath.stem == alias or filepath.stem.startswith(f"{alias}_") for alias in aliases):
        return True

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            corpus = json.load(f)
    except Exception:
        return False

    language = corpus.get("language", "")
    source = corpus.get("source", "")
    return language in aliases or any(source == alias or source.startswith(f"{alias}_") for alias in aliases)


def _find_corpus_files(language: str) -> list[Path]:
    if not language:
        return _unique_paths(list(OUTPUT_DIR.glob("*.json")) + list(OUTPUT_DIR.glob("*/*.json")))

    aliases = _language_aliases(language)
    corpus_files: list[Path] = []

    for alias in aliases:
        lang_dir = OUTPUT_DIR / alias
        if lang_dir.is_dir():
            corpus_files.extend(lang_dir.glob("*.json"))

    if corpus_files:
        return _unique_paths(corpus_files)

    # Backward compatibility: older conversions saved flat output/*.json files.
    return _unique_paths([
        filepath for filepath in OUTPUT_DIR.glob("*.json")
        if _flat_corpus_matches_language(filepath, aliases)
    ])


@router.post("/api/search")
async def search(request: SearchQuery):
    """
    Ищет по корпусу предложения, соответствующие запросу.

    Args:
        request: объект SearchQuery с параметрами поиска.

    Returns:
        JSON-ответ с найденными предложениями.
    """
    try:
        from lib.search_engine import search_corpus, load_corpus
    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail=f"Модуль ещё не доступен: {e}",
        )

    corpus_files = _find_corpus_files(request.language)

    if not corpus_files:
        raise HTTPException(
            status_code=404,
            detail=f"Корпус не найден. Сначала конвертируйте тексты через Транслятор.",
        )

    # Load and merge all corpus files
    all_sentences = []
    for cf in corpus_files:
        try:
            corpus = load_corpus(str(cf))
            if "sentences" in corpus:
                all_sentences.extend(corpus["sentences"])
        except Exception:
            continue

    if not all_sentences:
        raise HTTPException(
            status_code=404,
            detail="Корпус пуст. Сначала конвертируйте тексты через Транслятор.",
        )

    merged_corpus = {"sentences": all_sentences}

    # search_engine uses search_type "token" for surface form; UI sends "wordform"
    st = request.search_mode
    if st == "wordform":
        st = "token"

    pos = _normalize_to_str_list(request.pos)
    features = _normalize_features(request.features)
    additional = _normalize_to_str_list(request.additional)

    # Build query dict matching search_engine.search_corpus interface
    search_query = {
        "search_type": st,
    }
    if request.query:
        if request.search_mode == "lemma":
            search_query["lemma"] = request.query
        else:
            search_query["wordform"] = request.query
    if pos:
        search_query["pos"] = pos
    if features:
        search_query["features"] = features
    if additional:
        search_query["additional"] = additional

    try:
        results = search_corpus(corpus=merged_corpus, query=search_query)
    except Exception as e:
        logger.exception("Ошибка при поиске")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при поиске: {e}",
        )

    return JSONResponse(content={
        "language": request.language,
        "query": request.query,
        "search_mode": request.search_mode,
        "total": results.get("total", 0),
        "results": results.get("results", []),
    })
