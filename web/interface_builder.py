"""
Генератор HTML-страницы поиска по корпусу.

На основе языковой схемы (словарь грамматических категорий) автоматически
создаёт HTML-страницу с формой поиска: чекбоксы для частей речи,
категорий и дополнительных признаков.
"""

from lib.schema_loader import LanguageScheme


# Русские названия грамматических категорий
CATEGORY_LABELS: dict[str, str] = {
    "Case": "Падеж",
    "Number": "Число",
    "Person": "Лицо",
    "Mood": "Наклонение",
    "Aspect": "Вид",
    "VerbForm": "Форма глагола",
    "Clusivity": "Инклюзивность",
    "NounType": "Тип имени",
    "Tense": "Время",
    "Voice": "Залог",
    "Polarity": "Полярность",
    "Evident": "Эвиденциальность",
    "Definite": "Определённость",
    "Degree": "Степень",
    "NumType": "Тип числительного",
    "VerbType": "Тип глагола",
}

# Русские названия POS-тегов
POS_LABELS: dict[str, str] = {
    "NOUN": "Существительное",
    "VERB": "Глагол",
    "NUM": "Числительное",
    "ADV": "Наречие",
    "PRON": "Местоимение",
    "PROPN": "Имя собственное",
    "ADJ": "Прилагательное",
    "ADP": "Предлог/послелог",
    "AUX": "Вспомогательный глагол",
    "INTJ": "Междометие",
    "PART": "Частица",
    "CONJ": "Союз",
}

# Русские названия для дополнительных признаков
FEATURE_LABELS: dict[str, str] = {
    "Evident=Nfh": "Неочевидное наклонение",
    "Voice=Caus": "Каузатив",
    "Polarity=Neg": "Отрицание",
    "Tense=Fut": "Будущее время",
    "Poss=Yes": "Притяжательность",
    "Degree=Dim": "Уменьшительность",
    "Classifier=Yes": "Классификатор",
    "Predicative=Yes": "Предикативность",
    "Focus=Yes": "Фокус",
    "Emphatic=Yes": "Эмфатичность",
    "Question=Yes": "Вопросительность",
    "Coordinating=Yes": "Сочинительность",
    "Reflex=Yes": "Возвратность",
    "Reciprocal=Yes": "Взаимность",
    "Conces=Yes": "Уступительность",
    "Add=Yes": "Аддитивность",
    "Definite=Ind": "Неопределённость",
}


def _render_category_block(cat_name: str, values: list[str]) -> str:
    """Генерирует HTML-блок для одной грамматической категории."""
    label = CATEGORY_LABELS.get(cat_name, cat_name)
    checkboxes = ""
    for val in values:
        checkboxes += (
            f'        <label class="checkbox-label">'
            f'<input type="checkbox" name="features" value="{cat_name}={val}" '
            f'data-category="{cat_name}"> {val}</label>\n'
        )
    return (
        f'<div class="category-block">\n'
        f'  <div class="category-header" onclick="toggleCategory(this)">\n'
        f'    <span class="category-arrow">&#9654;</span> {label} ({cat_name})\n'
        f'  </div>\n'
        f'  <div class="category-body collapsed">\n'
        f'    <div class="category-actions">\n'
        f'      <button type="button" class="btn-small" '
        f'onclick="selectAllInCategory(this, \'{cat_name}\')">Выбрать все</button>\n'
        f'      <button type="button" class="btn-small" '
        f'onclick="clearAllInCategory(this, \'{cat_name}\')">Сбросить</button>\n'
        f'    </div>\n'
        f'    <div class="checkbox-list">\n'
        f'{checkboxes}'
        f'    </div>\n'
        f'  </div>\n'
        f'</div>\n'
    )


def _render_additional_features(features: list[str]) -> str:
    """Генерирует HTML-блок для дополнительных признаков."""
    if not features:
        return ""
    checkboxes = ""
    for feat in features:
        label = FEATURE_LABELS.get(feat, feat)
        checkboxes += (
            f'        <label class="checkbox-label">'
            f'<input type="checkbox" name="additional" value="{feat}"> '
            f'{label} ({feat})</label>\n'
        )
    return (
        '<div class="category-block">\n'
        '  <div class="category-header" onclick="toggleCategory(this)">\n'
        '    <span class="category-arrow">&#9654;</span> Дополнительные признаки\n'
        '  </div>\n'
        '  <div class="category-body collapsed">\n'
        '    <div class="checkbox-list">\n'
        f'{checkboxes}'
        '    </div>\n'
        '  </div>\n'
        '</div>\n'
    )


def _render_pos_checkboxes(pos_tags: list[str]) -> str:
    """Генерирует HTML-блок чекбоксов для частей речи."""
    checkboxes = ""
    for pos in pos_tags:
        label = POS_LABELS.get(pos, pos)
        checkboxes += (
            f'    <label class="checkbox-label">'
            f'<input type="checkbox" name="pos" value="{pos}"> '
            f'{label} ({pos})</label>\n'
        )
    return (
        '<div class="pos-block">\n'
        '  <h3>Часть речи</h3>\n'
        '  <div class="checkbox-list checkbox-list-inline">\n'
        f'{checkboxes}'
        '  </div>\n'
        '</div>\n'
    )


def build_search_page(scheme: LanguageScheme, language_name: str) -> str:
    """
    Генерирует полную HTML-страницу поиска по корпусу для данного языка.

    Args:
        scheme: языковая схема (LanguageScheme).
        language_name: название языка для отображения.

    Returns:
        Полный HTML-документ в виде строки.
    """
    # Собираем POS-теги из схемы
    pos_tags = ["NOUN", "VERB", "NUM", "ADV", "PRON", "PROPN"]

    # Категории из схемы
    categories_html = ""
    for cat_name, values in scheme.categories.items():
        categories_html += _render_category_block(cat_name, values)

    # Дополнительные признаки
    additional_html = _render_additional_features(scheme.additional_features)

    # POS-чекбоксы
    pos_html = _render_pos_checkboxes(pos_tags)

    language_code = scheme.language_code or language_name.lower()

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Поиск по корпусу — {language_name}</title>
    <link rel="stylesheet" href="/static/styles.css?v=3">
</head>
<body class="page-search">
    <header>
        <nav>
            <a href="/" class="nav-brand">Инструменты полевой лингвистики</a>
            <div class="nav-links">
                <a href="/">Главная</a>
                <a href="/translator">Транслятор</a>
                <a href="/lexicograph">Лексикограф</a>
            </div>
        </nav>
    </header>

    <main class="container page-shell">
        <section class="page-intro">
            <p class="eyebrow">Корпусный поиск</p>
            <h1>Поиск по корпусу: {language_name}</h1>
            <p class="page-description">
                Ищите словоформы, леммы и грамматические комбинации в аннотированном корпусе.
                Можно выполнять поиск по тексту, по части речи и по выбранным морфологическим признакам.
            </p>
        </section>

        <form id="searchForm" class="search-form">
            <input type="hidden" name="language" value="{language_code}">

            <div class="search-bar">
                <div class="search-input-group">
                    <input type="text" id="searchQuery" name="query"
                           placeholder="Введите поисковый запрос..."
                           class="search-input">
                    <div class="search-mode-toggle">
                        <label class="toggle-label">
                            <input type="radio" name="search_mode" value="wordform" checked>
                            Словоформа
                        </label>
                        <label class="toggle-label">
                            <input type="radio" name="search_mode" value="lemma">
                            Лемма
                        </label>
                    </div>
                </div>
            </div>

            {pos_html}

            <h3>Грамматические категории</h3>
            <div class="categories-grid">
                {categories_html}
            </div>

            {additional_html}

            <div class="form-actions">
                <button type="submit" class="btn btn-primary">Найти</button>
                <button type="button" class="btn btn-secondary" onclick="resetSearchForm()">Сбросить</button>
            </div>
        </form>

        <div id="searchResults" class="search-results" style="display: none;">
            <h2>Результаты поиска</h2>
            <div id="resultsCount" class="results-count"></div>
            <div id="resultsList"></div>
        </div>
    </main>

    <footer>
        <p>Инструменты полевой лингвистики</p>
    </footer>

    <script src="/static/app.js"></script>
    <script>
        document.getElementById('searchForm').addEventListener('submit', function(e) {{
            e.preventDefault();
            submitSearchForm('{language_code}');
        }});
    </script>
</body>
</html>"""
