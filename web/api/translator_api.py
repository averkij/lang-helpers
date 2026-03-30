"""
API-эндпоинты транслятора.

Принимает загруженный файл с глоссированным текстом и имя схемы,
возвращает результат в формате JSON или CoNLL-U.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"


@router.post("/api/translate")
async def translate(
    file: UploadFile = File(...),
    scheme_name: str = Form(...),
    output_format: str = Form("all"),
):
    """
    Конвертирует глоссированный текст в корпусный формат.

    Args:
        file: загруженный .txt файл с глоссированным текстом.
        scheme_name: имя языковой схемы (без расширения .py).
        output_format: формат вывода — 'json', 'conllu' или 'all'.

    Returns:
        JSON-ответ с результатами конвертации.
    """
    try:
        from lib.glossing_parser import parse_text
        from lib.translator import translate_to_json, translate_to_conllu
        from lib.schema_loader import load_scheme_by_name
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

    # Загрузка схемы
    try:
        scheme = load_scheme_by_name(scheme_name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Схема '{scheme_name}' не найдена.",
        )

    # Парсинг
    sentences = parse_text(text)
    if not sentences:
        raise HTTPException(
            status_code=400,
            detail="Не удалось разобрать ни одного предложения из файла.",
        )

    result = {
        "filename": file.filename,
        "scheme": scheme_name,
        "sentences_count": len(sentences),
    }

    try:
        from lib.translator import save_json, save_conllu

        source_name = Path(file.filename).stem if file.filename else "unknown"
        lang_dir = OUTPUT_DIR / scheme_name
        lang_dir.mkdir(parents=True, exist_ok=True)

        if output_format in ("json", "all"):
            json_data = translate_to_json(sentences, scheme, source_name)
            result["json"] = json_data
            save_json(json_data, str(lang_dir / f"{source_name}.json"))

        if output_format in ("conllu", "all"):
            conllu_text = translate_to_conllu(sentences, scheme)
            result["conllu"] = conllu_text
            save_conllu(conllu_text, str(lang_dir / f"{source_name}.conllu"))

    except Exception as e:
        logger.exception("Ошибка при конвертации")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при конвертации: {e}",
        )

    return JSONResponse(content=result)
