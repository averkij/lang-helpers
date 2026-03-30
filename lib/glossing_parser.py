"""
Парсер формата Лейпцигского глоссирования (Leipzig Glossing Rules).

Разбирает текстовые файлы с глоссированными предложениями в структурированные
объекты Python. Поддерживает дефисы (аффиксы), знаки равенства (клитики)
и точки (слитные категории).
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Morpheme:
    """Одна морфема с формой и глоссой."""
    form: str
    gloss: str
    is_grammatical: bool

    def __repr__(self) -> str:
        marker = "GRAM" if self.is_grammatical else "LEX"
        return f"Morpheme({self.form!r}, {self.gloss!r}, {marker})"


@dataclass
class Word:
    """Словоформа с разбивкой на морфемы."""
    form: str
    morphemes: list[Morpheme] = field(default_factory=list)

    @property
    def lemma(self) -> str:
        """Лемма — форма первой (корневой) морфемы."""
        if self.morphemes:
            return self.morphemes[0].form
        return self.form

    def __repr__(self) -> str:
        return f"Word({self.form!r}, {self.morphemes!r})"


@dataclass
class Sentence:
    """Полное глоссированное предложение."""
    id: str
    original: str
    words: list[Word] = field(default_factory=list)
    translation: str = ""

    def __repr__(self) -> str:
        return f"Sentence(id={self.id!r}, original={self.original!r}, words={len(self.words)}, translation={self.translation!r})"


# Регулярное выражение для разделения морфем: дефис или знак равенства
_MORPHEME_SPLIT_RE = re.compile(r'(?<=.)[-=](?=.)')

# Регулярное выражение для строки с номером предложения
_SENTENCE_ID_RE = re.compile(r'^(\d+)\s*>\s*(.*)')


def _is_grammatical_gloss(gloss: str) -> bool:
    """
    Определяет, является ли глосса грамматической.
    Грамматические глоссы записываются ЗАГЛАВНЫМИ буквами или цифрами (напр. 3SG, ABL, IND).
    Лексические глоссы — строчными (напр. человек, один).
    """
    # Убираем точки (слитные категории вроде 3SG разбирать не нужно для проверки)
    cleaned = gloss.replace(".", "")
    if not cleaned:
        return False
    return cleaned.isupper() or cleaned.isdigit() or bool(re.match(r'^[0-9A-Z]+$', cleaned))


def _split_morphemes(text: str) -> list[str]:
    """
    Разбивает словоформу на морфемы по дефисам и знакам равенства.
    Сохраняет разделитель для информации о типе границы.
    """
    return _MORPHEME_SPLIT_RE.split(text)


def _parse_word(segmented_form: str, gloss_form: str, sentence_id: str, word_idx: int) -> Word | None:
    """
    Разбирает одно слово: сопоставляет сегментированную форму и глоссы.
    Возвращает Word или None при критической ошибке.
    """
    morpheme_forms = _split_morphemes(segmented_form)
    morpheme_glosses = _split_morphemes(gloss_form)

    if len(morpheme_forms) != len(morpheme_glosses):
        logger.warning(
            f"Предложение {sentence_id}, слово #{word_idx + 1}: "
            f"несовпадение числа морфем в форме ({len(morpheme_forms)}: {segmented_form!r}) "
            f"и глоссе ({len(morpheme_glosses)}: {gloss_form!r}). "
            f"Пропускаем выравнивание морфем."
        )
        # Создаём слово без поморфемной разбивки — берём целиком
        is_gram = _is_grammatical_gloss(gloss_form)
        morphemes = [Morpheme(form=segmented_form, gloss=gloss_form, is_grammatical=is_gram)]
        return Word(form=segmented_form, morphemes=morphemes)

    morphemes = []
    for m_form, m_gloss in zip(morpheme_forms, morpheme_glosses):
        is_gram = _is_grammatical_gloss(m_gloss)
        morphemes.append(Morpheme(form=m_form, gloss=m_gloss, is_grammatical=is_gram))

    return Word(form=segmented_form, morphemes=morphemes)


def _parse_sentence_block(lines: list[str]) -> Sentence | None:
    """
    Разбирает блок строк, соответствующий одному предложению.
    Ожидает 4 строки: ID+оригинал, сегментация, глоссы, перевод.
    """
    if len(lines) < 4:
        logger.warning(
            f"Неполный блок предложения (найдено {len(lines)} строк, ожидается 4): "
            f"{lines!r}"
        )
        return None

    # Строка 1: номер и оригинальный текст
    id_match = _SENTENCE_ID_RE.match(lines[0])
    if not id_match:
        logger.warning(f"Не удалось распознать номер предложения в строке: {lines[0]!r}")
        return None

    sentence_id = id_match.group(1)
    original_text = id_match.group(2).strip()

    # Строка 2: морфемная сегментация
    segmented_line = lines[1].strip()

    # Строка 3: глоссы
    gloss_line = lines[2].strip()

    # Строка 4: свободный перевод (в кавычках)
    translation_line = lines[3].strip()
    # Убираем окружающие кавычки
    translation = translation_line.strip("'\"").strip()

    # Разбираем слова
    seg_words = segmented_line.split()
    gloss_words = gloss_line.split()

    if len(seg_words) != len(gloss_words):
        logger.warning(
            f"Предложение {sentence_id}: несовпадение числа слов "
            f"в сегментации ({len(seg_words)}) и глоссах ({len(gloss_words)}). "
            f"Сегментация: {segmented_line!r}, Глоссы: {gloss_line!r}"
        )
        # Обрабатываем сколько можем
        min_len = min(len(seg_words), len(gloss_words))
        seg_words = seg_words[:min_len]
        gloss_words = gloss_words[:min_len]

    words = []
    for i, (seg, gls) in enumerate(zip(seg_words, gloss_words)):
        word = _parse_word(seg, gls, sentence_id, i)
        if word is not None:
            words.append(word)

    return Sentence(
        id=sentence_id,
        original=original_text,
        words=words,
        translation=translation,
    )


def parse_file(filepath: str) -> list[Sentence]:
    """
    Разбирает файл с лейпцигским глоссированием.

    Args:
        filepath: путь к текстовому файлу с глоссированием.

    Returns:
        Список объектов Sentence.

    Raises:
        FileNotFoundError: если файл не найден.
        UnicodeDecodeError: при проблемах с кодировкой файла.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {filepath}")

    text = path.read_text(encoding="utf-8")
    return parse_text(text)


def parse_text(text: str) -> list[Sentence]:
    """
    Разбирает текст с лейпцигским глоссированием.

    Args:
        text: строка с глоссированным текстом.

    Returns:
        Список объектов Sentence.
    """
    lines = text.strip().split("\n")
    sentences = []

    # Собираем строки в блоки, разделённые пустыми строками
    blocks: list[list[str]] = []
    current_block: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if current_block:
                blocks.append(current_block)
                current_block = []
        else:
            current_block.append(stripped)

    if current_block:
        blocks.append(current_block)

    for block in blocks:
        sentence = _parse_sentence_block(block)
        if sentence is not None:
            sentences.append(sentence)

    logger.info(f"Разобрано {len(sentences)} предложений.")
    return sentences
