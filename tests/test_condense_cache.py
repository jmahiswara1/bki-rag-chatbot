import hashlib
import re
from unittest.mock import patch, MagicMock

import pytest

from src.llm.chain import (
    _normalize_for_cache,
    _cache_hash,
    _condense_cache_get,
    _condense_cache_put,
    _translate_condense,
    CONDENSE_CACHE_VERSION,
)


class TestCacheNormalization:
    def test_strips_and_collapses_whitespace(self):
        got = _normalize_for_cache("  hello   world  ")
        assert got == "hello world"

    def test_casefold_lowercases(self):
        got = _normalize_for_cache("Hello WORLD")
        assert got == "hello world"

    def test_id_query_unchanged_content(self):
        q = "Jika pelat sisi kapal memiliki tebal 4mm"
        got = _normalize_for_cache(q)
        assert "4mm" in got
        assert "pelat" in got

    def test_hash_deterministic(self):
        h1 = _cache_hash("id", "default", "test query")
        h2 = _cache_hash("id", "default", "test query")
        assert h1 == h2

    def test_hash_differs_by_lang(self):
        h1 = _cache_hash("id", "default", "test")
        h2 = _cache_hash("en", "default", "test")
        assert h1 != h2

    def test_hash_differs_by_mode(self):
        h1 = _cache_hash("id", "default", "test")
        h2 = _cache_hash("id", "fast", "test")
        assert h1 != h2

    def test_hash_differs_by_version(self):
        v1 = f"1|id|default|test"
        v2 = f"2|id|default|test"
        h1 = hashlib.sha256(v1.encode()).hexdigest()
        h2 = hashlib.sha256(v2.encode()).hexdigest()
        assert h1 != h2

    def test_hash_case_insensitive(self):
        h1 = _cache_hash("id", "default", _normalize_for_cache("TEST QUERY"))
        h2 = _cache_hash("id", "default", _normalize_for_cache("test query"))
        assert h1 == h2


class TestCondenseCache:
    def mock_supabase_client(self, select_data=None):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=select_data or [])
        return mock_client

    def test_cache_get_miss_returns_none(self):
        with patch("src.llm.chain.get_client") as mock_get:
            mock_get.return_value = self.mock_supabase_client([])
            result = _condense_cache_get("test query", "id", "default")
            assert result is None

    def test_cache_get_hit_returns_en_query(self):
        with patch("src.llm.chain.get_client") as mock_get:
            mock_get.return_value = self.mock_supabase_client(
                [{"en_query": "what is the plate thickness"}]
            )
            result = _condense_cache_get("test query", "id", "default")
            assert result == "what is the plate thickness"

    def test_cache_get_supabase_error_returns_none(self):
        with patch("src.llm.chain.get_client") as mock_get:
            mock_client = MagicMock()
            mock_client.table.side_effect = RuntimeError("connection failed")
            mock_get.return_value = mock_client
            result = _condense_cache_get("test query", "id", "default")
            assert result is None

    def test_cache_put_supabase_error_does_not_raise(self):
        with patch("src.llm.chain.get_client") as mock_get:
            mock_client = MagicMock()
            mock_client.table.side_effect = RuntimeError("connection failed")
            mock_get.return_value = mock_client
            # Must not raise
            _condense_cache_put("test query", "id", "default", "cached en query")

    def test_cache_put_calls_upsert(self):
        with patch("src.llm.chain.get_client") as mock_get:
            mock_client = self.mock_supabase_client()
            mock_table = mock_client.table.return_value
            mock_upsert = MagicMock()
            mock_table.upsert.return_value = mock_upsert
            mock_get.return_value = mock_client

            _condense_cache_put("test query", "id", "default", "cached result")

            mock_client.table.assert_called_with("query_condense_cache")
            mock_table.upsert.assert_called_once()

    def test_translate_condense_cache_hit_skips_llm(self):
        with patch("src.llm.chain._condense_cache_get") as mock_get, \
             patch("src.llm.chain._condense_cache_put") as mock_put:
            mock_get.return_value = "cached en query"

            result = _translate_condense(
                "apa itu kapal", [], temperature=0.0, mode="default", lang="id"
            )
            assert result == "cached en query"
            mock_put.assert_not_called()

    def test_translate_condense_cache_miss_calls_llm_and_stores(self):
        with patch("src.llm.chain._condense_cache_get") as mock_get, \
             patch("src.llm.chain._condense_cache_put") as mock_put, \
             patch("src.llm.chain.apply_glossary") as mock_gloss, \
             patch("src.llm.chain.chat") as mock_chat, \
             patch("src.llm.chain._clean_one_liner") as mock_clean:
            mock_get.return_value = None
            mock_gloss.return_value = "apa itu kapal"
            mock_chat.return_value = "what is a ship"
            mock_clean.return_value = "what is a ship"

            result = _translate_condense(
                "apa itu kapal", [], temperature=0.0, mode="default", lang="id"
            )
            assert result == "what is a ship"
            mock_put.assert_called_once()

    def test_translate_condense_no_cache_when_mode_none(self):
        with patch("src.llm.chain._condense_cache_get") as mock_get, \
             patch("src.llm.chain._condense_cache_put") as mock_put:
            mock_get.return_value = "should not be used"

            with patch("src.llm.chain.apply_glossary") as mock_gloss, \
                 patch("src.llm.chain.chat") as mock_chat, \
                 patch("src.llm.chain._clean_one_liner") as mock_clean:
                mock_gloss.return_value = "test"
                mock_chat.return_value = "live en query"
                mock_clean.return_value = "live en query"

                result = _translate_condense("test", [], temperature=0.0)
                assert result == "live en query"
                mock_get.assert_not_called()
                mock_put.assert_not_called()
