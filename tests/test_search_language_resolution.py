import json
import tempfile
import unittest
from pathlib import Path

from lib.schema_loader import load_scheme_by_name
from web import interface_builder
from web.api import search_api


class SearchLanguageResolutionTests(unittest.TestCase):
    def test_search_page_submits_route_scheme_name(self):
        scheme = load_scheme_by_name("karaim")

        html = interface_builder.build_search_page(
            scheme,
            scheme.language_name,
            language_id="karaim",
        )

        self.assertIn("submitSearchForm('karaim')", html)
        self.assertNotIn("submitSearchForm('kdr')", html)

    def test_corpus_lookup_resolves_iso_code_to_scheme_output_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_output_dir = search_api.OUTPUT_DIR
            search_api.OUTPUT_DIR = Path(tmpdir)
            try:
                corpus_dir = Path(tmpdir) / "karaim"
                corpus_dir.mkdir()
                corpus_file = corpus_dir / "karaim_sample.json"
                corpus_file.write_text(
                    json.dumps({"language": "kdr", "sentences": []}),
                    encoding="utf-8",
                )

                self.assertEqual(search_api._find_corpus_files("kdr"), [corpus_file])
                self.assertEqual(search_api._find_corpus_files("karaim"), [corpus_file])
            finally:
                search_api.OUTPUT_DIR = old_output_dir

    def test_flat_fallback_is_limited_to_requested_language(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_output_dir = search_api.OUTPUT_DIR
            search_api.OUTPUT_DIR = Path(tmpdir)
            try:
                nivkh_file = Path(tmpdir) / "nivkh_sample.json"
                nivkh_file.write_text(
                    json.dumps({"language": "niv", "sentences": []}),
                    encoding="utf-8",
                )
                karaim_file = Path(tmpdir) / "karaim_sample.json"
                karaim_file.write_text(
                    json.dumps({"language": "kdr", "sentences": []}),
                    encoding="utf-8",
                )

                self.assertEqual(search_api._find_corpus_files("kdr"), [karaim_file])
                self.assertEqual(search_api._find_corpus_files("niv"), [nivkh_file])
            finally:
                search_api.OUTPUT_DIR = old_output_dir


if __name__ == "__main__":
    unittest.main()
