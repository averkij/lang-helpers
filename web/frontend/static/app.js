/**
 * Клиентский JavaScript для инструментов полевой лингвистики.
 *
 * Обработка загрузки файлов, AJAX-запросы к API,
 * отображение результатов, управление формой поиска.
 */

/* === Утилиты === */

/**
 * Показывает сообщение о статусе.
 */
function showStatus(elementId, message, type) {
    var el = document.getElementById(elementId);
    if (!el) return;
    el.textContent = message;
    el.className = 'status-message ' + type;
    el.style.display = 'block';
}

/**
 * Скрывает сообщение о статусе.
 */
function hideStatus(elementId) {
    var el = document.getElementById(elementId);
    if (el) el.style.display = 'none';
}

/**
 * Экранирование HTML-символов.
 */
function escapeHtml(text) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}


/* === Загрузка файлов === */

/**
 * Настраивает область загрузки файлов с drag-and-drop.
 */
function setupFileUpload(inputId, dropAreaId, fileNameId) {
    var fileInput = document.getElementById(inputId);
    var dropArea = document.getElementById(dropAreaId);
    var fileNameEl = document.getElementById(fileNameId);

    if (!fileInput || !dropArea) return;

    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) {
            fileNameEl.textContent = fileInput.files[0].name;
        }
    });

    dropArea.addEventListener('dragover', function (e) {
        e.preventDefault();
        dropArea.classList.add('dragover');
    });

    dropArea.addEventListener('dragleave', function () {
        dropArea.classList.remove('dragover');
    });

    dropArea.addEventListener('drop', function (e) {
        e.preventDefault();
        dropArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            fileNameEl.textContent = e.dataTransfer.files[0].name;
        }
    });
}


/* === Транслятор === */

/** Глобальное хранилище результатов транслятора. */
var translatorData = {};

/**
 * Загружает список доступных схем в выпадающий список.
 */
function loadSchemes() {
    fetch('/api/schemes')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var sel = document.getElementById('schemeSelect');
            if (!sel) return;
            sel.innerHTML = '';
            if (data.schemes && data.schemes.length > 0) {
                data.schemes.forEach(function (name) {
                    var opt = document.createElement('option');
                    opt.value = name;
                    opt.textContent = name;
                    sel.appendChild(opt);
                });
            } else {
                var opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'Схемы не найдены';
                sel.appendChild(opt);
            }
        })
        .catch(function () {
            var sel = document.getElementById('schemeSelect');
            if (sel) {
                sel.innerHTML = '<option value="">Ошибка загрузки схем</option>';
            }
        });
}

/**
 * Отправляет файл на конвертацию.
 */
function translateFile(format) {
    var fileInput = document.getElementById('fileInput');
    var schemeSelect = document.getElementById('schemeSelect');

    if (!fileInput || !fileInput.files.length) {
        showStatus('translatorStatus', 'Выберите файл для конвертации.', 'error');
        return;
    }

    if (!schemeSelect || !schemeSelect.value) {
        showStatus('translatorStatus', 'Выберите языковую схему.', 'error');
        return;
    }

    var formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('scheme_name', schemeSelect.value);
    formData.append('output_format', format);

    showStatus('translatorStatus', 'Конвертация...', 'loading');
    document.getElementById('translatorResults').style.display = 'none';

    fetch('/api/translate', {
        method: 'POST',
        body: formData,
    })
        .then(function (r) {
            if (!r.ok) {
                return r.json().then(function (err) {
                    throw new Error(err.detail || 'Ошибка сервера');
                });
            }
            return r.json();
        })
        .then(function (data) {
            translatorData = data;
            hideStatus('translatorStatus');
            showTranslatorResults(data);
        })
        .catch(function (err) {
            showStatus('translatorStatus', 'Ошибка: ' + err.message, 'error');
        });
}

/**
 * Отображает результаты конвертации.
 */
function showTranslatorResults(data) {
    var section = document.getElementById('translatorResults');
    var meta = document.getElementById('resultsMeta');
    section.style.display = 'block';

    meta.textContent = 'Файл: ' + (data.filename || '?') +
        ' | Схема: ' + (data.scheme || '?') +
        ' | Предложений: ' + (data.sentences_count || 0);

    var jsonSection = document.getElementById('jsonResult');
    var conlluSection = document.getElementById('conlluResult');

    if (data.json !== undefined) {
        jsonSection.style.display = 'block';
        document.getElementById('jsonOutput').textContent =
            typeof data.json === 'string' ? data.json : JSON.stringify(data.json, null, 2);
    } else {
        jsonSection.style.display = 'none';
    }

    if (data.conllu !== undefined) {
        conlluSection.style.display = 'block';
        document.getElementById('conlluOutput').textContent = data.conllu;
    } else {
        conlluSection.style.display = 'none';
    }
}

/**
 * Скачивает результат конвертации.
 */
function downloadResult(format) {
    var content, filename, mime;
    if (format === 'json' && translatorData.json !== undefined) {
        content = typeof translatorData.json === 'string'
            ? translatorData.json
            : JSON.stringify(translatorData.json, null, 2);
        filename = (translatorData.filename || 'result').replace(/\.txt$/, '') + '.json';
        mime = 'application/json';
    } else if (format === 'conllu' && translatorData.conllu !== undefined) {
        content = translatorData.conllu;
        filename = (translatorData.filename || 'result').replace(/\.txt$/, '') + '.conllu';
        mime = 'text/plain';
    } else {
        return;
    }
    downloadBlob(content, filename, mime);
}

/**
 * Копирует результат конвертации в буфер обмена.
 */
function copyResult(format) {
    var el = document.getElementById(format === 'json' ? 'jsonOutput' : 'conlluOutput');
    if (el) {
        navigator.clipboard.writeText(el.textContent).then(function () {
            showStatus('translatorStatus', 'Скопировано в буфер обмена.', 'success');
            setTimeout(function () { hideStatus('translatorStatus'); }, 2000);
        });
    }
}


/* === Лексикограф === */

/** Глобальное хранилище данных словника. */
var dictionaryData = null;

/**
 * Отправляет файл для создания словника.
 */
function buildDictionary() {
    var fileInput = document.getElementById('lexFileInput');

    if (!fileInput || !fileInput.files.length) {
        showStatus('lexStatus', 'Выберите файл для создания словника.', 'error');
        return;
    }

    var formData = new FormData();
    formData.append('file', fileInput.files[0]);

    showStatus('lexStatus', 'Создание словника...', 'loading');
    document.getElementById('lexResults').style.display = 'none';

    fetch('/api/lexicograph', {
        method: 'POST',
        body: formData,
    })
        .then(function (r) {
            if (!r.ok) {
                return r.json().then(function (err) {
                    throw new Error(err.detail || 'Ошибка сервера');
                });
            }
            return r.json();
        })
        .then(function (data) {
            dictionaryData = data;
            hideStatus('lexStatus');
            showDictionaryResults(data);
        })
        .catch(function (err) {
            showStatus('lexStatus', 'Ошибка: ' + err.message, 'error');
        });
}

/**
 * Отображает результаты создания словника.
 */
function showDictionaryResults(data) {
    var section = document.getElementById('lexResults');
    var meta = document.getElementById('lexMeta');
    var preview = document.getElementById('dictionaryPreview');
    section.style.display = 'block';

    var dict = data.dictionary;
    if (!dict) {
        preview.innerHTML = '<p>Словник пуст.</p>';
        return;
    }

    var metadata = dict.metadata || {};
    meta.textContent = 'Файл: ' + (data.filename || '?') +
        ' | Предложений: ' + (data.sentences_count || 0) +
        ' | Словоформ: ' + (metadata.unique_words || 0) +
        ' | Морфем: ' + (metadata.unique_morphemes || 0);

    preview.innerHTML = '';

    var wordEntries = dict.word_dictionary || [];
    var morphEntries = dict.morpheme_dictionary || [];

    if (wordEntries.length > 0) {
        var h3 = document.createElement('h3');
        h3.textContent = 'Словник (' + wordEntries.length + ')';
        preview.appendChild(h3);
        renderDictEntries(preview, wordEntries);
    }

    if (morphEntries.length > 0) {
        var h3m = document.createElement('h3');
        h3m.textContent = 'Словарь морфем (' + morphEntries.length + ')';
        preview.appendChild(h3m);
        renderDictEntries(preview, morphEntries);
    }
}

function renderDictEntries(container, entries) {
    entries.forEach(function (entry) {
        var div = document.createElement('div');
        div.className = 'dict-entry';

        var source = entry.source || '';
        var target = entry.target || '';
        var count = entry.citations ? entry.citations.length : 0;

        var html = '<span class="dict-lemma">' + escapeHtml(source) + '</span>';
        if (count) html += '<span class="dict-count">[' + count + ']</span>';
        if (target) html += '<span class="dict-translation"> — ' + escapeHtml(target) + '</span>';

        div.innerHTML = html;
        container.appendChild(div);
    });
}

/**
 * Скачивает словник в выбранном формате.
 */
function downloadDictionary(format) {
    if (!dictionaryData || !dictionaryData.dictionary) return;

    var dict = dictionaryData.dictionary;
    var content, filename, mime;
    if (format === 'json') {
        content = JSON.stringify(dict, null, 2);
        filename = 'dictionary.json';
        mime = 'application/json';
    } else {
        var lines = [];
        var wordEntries = dict.word_dictionary || [];
        var morphEntries = dict.morpheme_dictionary || [];

        lines.push('Словник');
        lines.push('');
        wordEntries.forEach(function (entry) {
            var cites = entry.citations ? entry.citations.join(', ') : '';
            lines.push(entry.source + '\t\t' + (entry.target || '') + '\t\t' + cites);
        });

        lines.push('');
        lines.push('Словарь морфем');
        lines.push('');
        morphEntries.forEach(function (entry) {
            var cites = entry.citations ? entry.citations.join(', ') : '';
            lines.push(entry.source + '\t\t' + (entry.target || '') + '\t\t' + cites);
        });

        var meta = dict.metadata || {};
        if (meta.total_words !== undefined) {
            lines.push('');
            lines.push('Статистика');
            lines.push('  Всего словоформ: ' + (meta.total_words || 0));
            lines.push('  Уникальных словоформ: ' + (meta.unique_words || 0));
            lines.push('  Всего морфем: ' + (meta.total_morphemes || 0));
            lines.push('  Уникальных морфем: ' + (meta.unique_morphemes || 0));
        }

        content = lines.join('\n');
        filename = 'dictionary.txt';
        mime = 'text/plain';
    }
    downloadBlob(content, filename, mime);
}

/**
 * Копирует словник в буфер обмена.
 */
function copyDictionary() {
    if (!dictionaryData || !dictionaryData.dictionary) return;
    var content = JSON.stringify(dictionaryData.dictionary, null, 2);
    navigator.clipboard.writeText(content).then(function () {
        showStatus('lexStatus', 'Скопировано в буфер обмена.', 'success');
        setTimeout(function () { hideStatus('lexStatus'); }, 2000);
    });
}


/* === Поиск по корпусу === */

/**
 * Переключает раскрытие блока категории.
 */
function toggleCategory(headerEl) {
    var body = headerEl.nextElementSibling;
    if (body.classList.contains('collapsed')) {
        body.classList.remove('collapsed');
        headerEl.classList.add('open');
    } else {
        body.classList.add('collapsed');
        headerEl.classList.remove('open');
    }
}

/**
 * Выбирает все чекбоксы в категории.
 */
function selectAllInCategory(btn, categoryName) {
    var block = btn.closest('.category-body');
    var checkboxes = block.querySelectorAll('input[data-category="' + categoryName + '"]');
    checkboxes.forEach(function (cb) { cb.checked = true; });
}

/**
 * Сбрасывает все чекбоксы в категории.
 */
function clearAllInCategory(btn, categoryName) {
    var block = btn.closest('.category-body');
    var checkboxes = block.querySelectorAll('input[data-category="' + categoryName + '"]');
    checkboxes.forEach(function (cb) { cb.checked = false; });
}

/**
 * Сбрасывает всю форму поиска.
 */
function resetSearchForm() {
    var form = document.getElementById('searchForm');
    if (!form) return;
    form.reset();
    document.getElementById('searchResults').style.display = 'none';
}

/**
 * Отправляет форму поиска.
 */
function submitSearchForm(languageCode) {
    var form = document.getElementById('searchForm');
    if (!form) return;

    var query = document.getElementById('searchQuery').value;
    var searchMode = form.querySelector('input[name="search_mode"]:checked').value;

    // Собираем выбранные POS
    var posChecked = [];
    form.querySelectorAll('input[name="pos"]:checked').forEach(function (cb) {
        posChecked.push(cb.value);
    });

    // Собираем выбранные признаки (API: категория -> список значений, ИЛИ внутри категории)
    var featuresObj = {};
    form.querySelectorAll('input[name="features"]:checked').forEach(function (cb) {
        var eq = cb.value.indexOf('=');
        if (eq === -1) return;
        var cat = cb.value.slice(0, eq);
        var val = cb.value.slice(eq + 1);
        if (!featuresObj[cat]) featuresObj[cat] = [];
        featuresObj[cat].push(val);
    });

    // Дополнительные признаки
    var additionalChecked = [];
    form.querySelectorAll('input[name="additional"]:checked').forEach(function (cb) {
        additionalChecked.push(cb.value);
    });

    var payload = {
        language: languageCode,
        query: query,
        search_mode: searchMode,
        pos: posChecked,
        features: featuresObj,
        additional: additionalChecked,
    };

    var resultsDiv = document.getElementById('searchResults');
    var countDiv = document.getElementById('resultsCount');
    var listDiv = document.getElementById('resultsList');

    resultsDiv.style.display = 'block';
    countDiv.textContent = 'Поиск...';
    listDiv.innerHTML = '';

    fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
        .then(function (r) {
            if (!r.ok) {
                return r.json().then(function (err) {
                    throw new Error(err.detail || 'Ошибка сервера');
                });
            }
            return r.json();
        })
        .then(function (data) {
            displaySearchResults(data, query);
        })
        .catch(function (err) {
            countDiv.textContent = 'Ошибка: ' + err.message;
        });
}

/**
 * Отображает результаты поиска.
 */
function displaySearchResults(data, query) {
    var countDiv = document.getElementById('resultsCount');
    var listDiv = document.getElementById('resultsList');

    var total = data.total || 0;
    countDiv.textContent = 'Найдено результатов: ' + total;

    listDiv.innerHTML = '';

    if (!data.results || data.results.length === 0) {
        listDiv.innerHTML = '<p>Ничего не найдено.</p>';
        return;
    }

    data.results.forEach(function (result) {
        var div = document.createElement('div');
        div.className = 'result-sentence';

        var sentenceId = result.id || result.sentence_id || '';
        var original = result.original || result.text || '';
        var translation = result.translation || '';
        var matchedIndices = result.matched_indices || result.highlights || [];

        // Подсветка совпадений
        var displayText = original;
        if (query && query.trim()) {
            var regex = new RegExp('(' + escapeRegex(query) + ')', 'gi');
            displayText = escapeHtml(original).replace(regex, '<span class="highlight">$1</span>');
        } else if (matchedIndices.length > 0) {
            // Подсветка по индексам слов
            var words = original.split(/\s+/);
            displayText = words.map(function (w, i) {
                var escaped = escapeHtml(w);
                if (matchedIndices.indexOf(i) !== -1) {
                    return '<span class="highlight">' + escaped + '</span>';
                }
                return escaped;
            }).join(' ');
        } else {
            displayText = escapeHtml(original);
        }

        var html = '';
        if (sentenceId) {
            html += '<div class="result-sentence-id">#' + escapeHtml(String(sentenceId)) + '</div>';
        }
        html += '<div class="result-sentence-original">' + displayText + '</div>';
        if (translation) {
            html += '<div class="result-sentence-translation">' + escapeHtml(translation) + '</div>';
        }

        div.innerHTML = html;
        listDiv.appendChild(div);
    });
}

/**
 * Экранирование спецсимволов для регулярных выражений.
 */
function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}


/* === Главная страница === */

/**
 * Загружает список доступных языков на главную страницу.
 */
function loadAvailableLanguages() {
    var container = document.getElementById('languagesList');
    if (!container) return;

    fetch('/api/schemes')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            container.innerHTML = '';
            if (data.schemes && data.schemes.length > 0) {
                data.schemes.forEach(function (name) {
                    var a = document.createElement('a');
                    a.href = '/search/' + name;
                    a.className = 'language-tag';
                    a.textContent = name;
                    container.appendChild(a);
                });
            } else {
                container.innerHTML = '<p>Языковые схемы не найдены.</p>';
            }
        })
        .catch(function () {
            container.innerHTML = '<p>Не удалось загрузить список языков.</p>';
        });
}


/* === Общие утилиты === */

/**
 * Скачивает текст как файл.
 */
function downloadBlob(content, filename, mimeType) {
    var blob = new Blob([content], { type: mimeType + ';charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
