import logging
import unittest
from pathlib import Path

from lib.glossing_parser import parse_file, parse_text
from lib.schema_loader import load_scheme_by_name
from lib.translator import translate_to_conllu, translate_to_json


ROOT = Path(__file__).resolve().parents[1]
KARAIM_SAMPLE = ROOT / "data" / "samples" / "karaim_sample.txt"
PARSER_LOGGER = logging.getLogger("lib.glossing_parser")
PARSER_LOGGER.addHandler(logging.NullHandler())
PARSER_LOGGER.propagate = False


class GlossingParserTests(unittest.TestCase):
    def test_legacy_four_line_block_still_parses(self):
        text = """1> foo-a bar
foo-a bar
root-ABL baz
'A test translation'
"""
        sentences = parse_text(text)

        self.assertEqual(len(sentences), 1)
        self.assertEqual(sentences[0].id, "1")
        self.assertEqual(sentences[0].original, "foo-a bar")
        self.assertEqual(sentences[0].translation, "A test translation")
        self.assertEqual([word.form for word in sentences[0].words], ["foo-a", "bar"])

    def test_karaim_numbered_sample_parses_twenty_three_sentences(self):
        sentences = parse_file(str(KARAIM_SAMPLE))

        self.assertEqual(len(sentences), 23)
        self.assertEqual(sentences[0].id, "1")
        self.assertEqual(sentences[-1].id, "23")
        self.assertTrue(sentences[19].translation.startswith("Как ни полезна вещь"))
        self.assertTrue(sentences[20].translation.startswith("Невежда про нее"))

    def test_bom_comments_and_translation_spans(self):
        text = """\ufeff# file comment
1> One
1< один
1= First translation
# inline comment

2> Two words
2< два слова

3> Three
3< три
2_3= Shared translation
"""
        sentences = parse_text(text)

        self.assertEqual([sentence.id for sentence in sentences], ["1", "2", "3"])
        self.assertEqual(sentences[0].translation, "First translation")
        self.assertEqual(sentences[1].translation, "Shared translation")
        self.assertEqual(sentences[2].translation, "Shared translation")

    def test_numbered_prefixes_do_not_enter_tokens_or_glosses(self):
        sentences = parse_text("""14> Bar-y-n kioz-liuk-liar učiun maja alde-j-dlar;
14< все-3.SG-ACC глаза-NMN-PL для я.DAT лгать-PRS-3.PL
14= Всё про Очки лишь мне налгали;
""")
        sentence = sentences[0]
        tokens = [word.form for word in sentence.words]
        glosses = [morpheme.gloss for word in sentence.words for morpheme in word.morphemes]

        self.assertEqual(len(tokens), 5)
        self.assertNotIn("14<", tokens)
        self.assertNotIn("14=", tokens)
        self.assertNotIn("14<", glosses)
        self.assertNotIn("Всё", tokens)
        self.assertNotIn("про", tokens)


class TranslatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sentences = parse_file(str(KARAIM_SAMPLE))
        cls.scheme = load_scheme_by_name("karaim")
        cls.json_data = translate_to_json(cls.sentences, cls.scheme, "karaim_sample")
        cls.conllu = translate_to_conllu(cls.sentences, cls.scheme)

    def test_sentence_14_json_has_source_translation_and_real_tokens(self):
        sentence = next(s for s in self.json_data["sentences"] if s["id"] == "14")
        tokens = [token["token"] for token in sentence["tokens"]]

        self.assertTrue(sentence["text"].startswith("Bar-y-n"))
        self.assertEqual(sentence["translation"], "Всё про Очки лишь мне налгали;")
        self.assertEqual(tokens, ["Bar-y-n", "kioz-liuk-liar", "učiun", "maja", "alde-j-dlar;"])
        self.assertNotIn("14<", tokens)
        self.assertNotIn("14=", tokens)
        self.assertNotIn("Всё", tokens)
        self.assertNotIn("про", tokens)

    def test_conllu_uses_numbered_text_and_translation_metadata(self):
        self.assertIn("# sent_id = 14", self.conllu)
        self.assertIn("# text = Bar-y-n", self.conllu)
        self.assertIn("# translation = Всё про Очки лишь мне налгали;", self.conllu)

    def test_schema_pos_mappings_set_upos_without_pos_features(self):
        sent_1 = next(s for s in self.json_data["sentences"] if s["id"] == "1")
        sent_2 = next(s for s in self.json_data["sentences"] if s["id"] == "2")
        sent_6 = next(s for s in self.json_data["sentences"] if s["id"] == "6")

        noun_token = sent_1["tokens"][2]
        verb_token = sent_2["tokens"][2]
        aux_token = sent_6["tokens"][3]

        self.assertEqual(noun_token["pos"], "NOUN")
        self.assertEqual(verb_token["pos"], "VERB")
        self.assertEqual(aux_token["pos"], "AUX")

        for token in (noun_token, verb_token, aux_token):
            features = token["tagsets"][0] if token["tagsets"] else []
            self.assertFalse(any(feature.startswith("POS=") for feature in features))


if __name__ == "__main__":
    unittest.main()
