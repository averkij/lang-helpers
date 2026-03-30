"""
API-эндпоинты поиска по корпусу.

Принимает поисковый запрос в формате JSON,
возвращает найденные предложения с подсвеченными совпадениями.
"""

import logging
import glob as glob_module
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

    # Find corpus files for this language in output/<language>/
    lang_dir = OUTPUT_DIR / request.language if request.language else OUTPUT_DIR
    corpus_files = list(lang_dir.glob("*.json")) if lang_dir.is_dir() else []

    # Fallback: also check flat output/*.json for backward compatibility
    if not corpus_files:
        corpus_files = list(OUTPUT_DIR.glob("*.json"))

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
