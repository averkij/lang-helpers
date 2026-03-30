"""
API-эндпоинты лексикографа.

Принимает загруженный файл с глоссированным текстом,
возвращает словник в формате JSON.
"""

import logging

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/lexicograph")
async def lexicograph(
    file: UploadFile = File(...),
):
    """
    Создаёт словник из глоссированного текста.

    Args:
        file: загруженный .txt файл с глоссированным текстом.

    Returns:
        JSON-ответ со словником.
    """
    try:
        from lib.glossing_parser import parse_text
        from lib.lexicograph import build_dictionaries_from_parsed
    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail=f"Модуль ещё не доступен: {e}",
        )

    # Чтение файла
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Не удалось прочитать файл. Убедитесь, что файл в кодировке UTF-8.",
        )

    # Парсинг
    sentences = parse_text(text)
    if not sentences:
        raise HTTPException(
            status_code=400,
            detail="Не удалось разобрать ни одного предложения из файла.",
        )

    try:
        dictionary = build_dictionaries_from_parsed(sentences)
    except Exception as e:
        logger.exception("Ошибка при создании словника")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании словника: {e}",
        )

    result = {
        "filename": file.filename,
        "sentences_count": len(sentences),
        "dictionary": dictionary,
    }

    return JSONResponse(content=result)
