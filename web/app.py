"""
Главное FastAPI-приложение для инструментов полевой лингвистики.

Запуск:
    cd D:\\git2\\minor-langs
    python -m uvicorn web.app:app --reload
"""

import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from web.api.translator_api import router as translator_router
from web.api.lexicograph_api import router as lexicograph_router
from web.api.search_api import router as search_router
from web.interface_builder import build_search_page

# Пути к файлам
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

app = FastAPI(
    title="Инструменты полевой лингвистики",
    description="Автоматизация полевой лингвистической работы",
    version="0.1.0",
)

# Статические файлы
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Подключаем роутеры API
app.include_router(translator_router)
app.include_router(lexicograph_router)
app.include_router(search_router)


def _read_html(filename: str) -> str:
    """Читает HTML-файл из директории frontend/."""
    filepath = os.path.join(FRONTEND_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/", response_class=HTMLResponse)
async def index():
    """Главная страница — панель инструментов."""
    return _read_html("index.html")


@app.get("/translator", response_class=HTMLResponse)
async def translator_page():
    """Страница транслятора."""
    return _read_html("translator.html")


@app.get("/lexicograph", response_class=HTMLResponse)
async def lexicograph_page():
    """Страница лексикографа."""
    return _read_html("lexicograph.html")


@app.get("/search/{language}", response_class=HTMLResponse)
async def search_page(language: str):
    """Автоматически сгенерированная страница поиска по корпусу."""
    from lib.schema_loader import load_scheme_by_name

    try:
        scheme = load_scheme_by_name(language)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Языковая схема '{language}' не найдена.",
        )

    html = build_search_page(scheme, scheme.language_name)
    return HTMLResponse(content=html)


@app.get("/api/schemes")
async def list_schemes():
    """Возвращает список доступных языковых схем."""
    from lib.schema_loader import list_available_schemes

    schemes = list_available_schemes()
    return JSONResponse(content={"schemes": schemes})
