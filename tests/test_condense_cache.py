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
    canonicalize_condensed_query,
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

    def test_cache_hit_stale_version_miss(self):
        """Old-version cache rows are ignored; hit only on matching version."""
        q = "apa tujuan pemasangan breakwater di geladak depan?"
        norm = _normalize_for_cache(q)
        old_hash = hashlib.sha256(
            f"1|id|default|{norm}".encode()
        ).hexdigest()
        new_hash = _cache_hash("id", "default", norm)
        assert old_hash != new_hash

    def test_cache_version_bump_changes_hash(self):
        """v2 → v3 bump: same text/lang/mode produces different hash."""
        q = "Apa tujuan pemasangan breakwater di geladak depan?"
        norm = _normalize_for_cache(q)
        h_v3 = _cache_hash("id", "default", norm)
        v2 = f"2|id|default|{norm}"
        h_v2 = hashlib.sha256(v2.encode()).hexdigest()
        assert h_v3 != h_v2

    def test_cache_miss_with_forward_deck_canonicalization(self):
        """Cache miss -> LLM gets pure ID, hallucinates 'on the dock',
        post-condense canonicalization fixes to 'forward deck'."""
        with patch("src.llm.chain._condense_cache_get") as mock_get, \
             patch("src.llm.chain._condense_cache_put") as mock_put, \
             patch("src.llm.chain.chat") as mock_chat, \
             patch("src.llm.chain._clean_one_liner") as mock_clean:
            mock_get.return_value = None
            mock_chat.return_value = "what is the purpose of installing a breakwater on the dock"
            mock_clean.return_value = "what is the purpose of installing a breakwater on the dock"

            result = _translate_condense(
                "Apa tujuan pemasangan breakwater di geladak depan?",
                [], temperature=0.0, mode="default", lang="id"
            )
            assert "forward deck" in result
            assert "dock" not in result
            assert "breakwater" in result
            mock_put.assert_called_once()

    def test_bulwark_on_dock_canonicalized_to_forward_deck(self):
        """Raw 'bulwark on the dock' + geladak depan original →
        'bulwark on the forward deck', NOT 'bilge keel'."""
        with patch("src.llm.chain._condense_cache_get") as mock_get, \
             patch("src.llm.chain._condense_cache_put") as mock_put, \
             patch("src.llm.chain.chat") as mock_chat, \
             patch("src.llm.chain._clean_one_liner") as mock_clean:
            mock_get.return_value = None
            mock_chat.return_value = "what are the height requirements for bulwark on the dock"
            mock_clean.return_value = "what are the height requirements for bulwark on the dock"

            result = _translate_condense(
                "Apa persyaratan tinggi bulwark di geladak depan?",
                [], temperature=0.0, mode="default", lang="id"
            )
            assert "forward deck" in result
            assert "bulwark" in result
            assert "bilge keel" not in result
            mock_put.assert_called_once()

    def test_hatch_forward_deck_unchanged(self):
        """Canonicalization is idempotent: already-correct 'forward deck' stays."""
        orig = "persyaratan hatch di geladak depan"
        en = "hatch requirements on the forward deck"
        result = canonicalize_condensed_query(orig, en)
        assert "forward deck" in result
        assert "hatch" in result

    def test_di_depan_dermaga_no_trigger(self):
        """'di depan dermaga' without geladak depan → no canonicalization."""
        r = canonicalize_condensed_query(
            "apa yang berada di depan dermaga?",
            "what is located in front of the dock"
        )
        assert "forward deck" not in r

    def test_area_depan_kapal_no_trigger(self):
        """'area depan kapal' without 'geladak depan' → no canonicalization."""
        r = canonicalize_condensed_query(
            "area depan kapal",
            "front area of the ship"
        )
        assert "forward deck" not in r

    def test_geladak_belakang_no_trigger(self):
        """'geladak belakang' ≠ 'geladak depan' → no canonicalization."""
        r = canonicalize_condensed_query(
            "geladak belakang kapal",
            "aft deck of the ship"
        )
        assert "forward deck" not in r

    def test_geladak_cuaca_no_trigger(self):
        """'geladak cuaca' → no canonicalization."""
        r = canonicalize_condensed_query(
            "geladak cuaca kapal",
            "weather deck of the ship"
        )
        assert "forward deck" not in r

    def test_geladak_terbuka_no_trigger(self):
        """'geladak terbuka' → no canonicalization."""
        r = canonicalize_condensed_query(
            "geladak terbuka kapal",
            "open deck of the ship"
        )
        assert "forward deck" not in r

    def test_canonicalization_idempotent(self):
        orig = "Apa tujuan pemasangan breakwater di geladak depan?"
        en = "what is the purpose of installing a breakwater on the forward deck"
        r1 = canonicalize_condensed_query(orig, en)
        r2 = canonicalize_condensed_query(orig, r1)
        assert r1 == r2
        assert "forward deck" in r1

    def test_capitalization_variant_trigger(self):
        r = canonicalize_condensed_query(
            "breakwater di GELADAK DEPAN kapal",
            "breakwater on the dock"
        )
        assert "forward deck" in r

    def test_whitespace_variant_trigger(self):
        r = canonicalize_condensed_query(
            "breakwater di  geladak  depan  kapal",
            "breakwater on the dock"
        )
        assert "forward deck" in r

    def test_v2_cached_bad_bulwark_not_used(self):
        """Version 3 hash ≠ version 2 hash, so v2 cached rows are misses."""
        q = "Apa persyaratan tinggi bulwark di geladak depan?"
        norm = _normalize_for_cache(q)
        v2_hash = hashlib.sha256(
            f"2|id|default|{norm}".encode()
        ).hexdigest()
        v3_hash = _cache_hash("id", "default", norm)
        assert v2_hash != v3_hash

    def test_v3_miss_hit_identical(self):
        """Cache miss produces canonical output; cache hit returns same."""
        orig = "Apa persyaratan tinggi bulwark di geladak depan?"
        en_raw = "what are the height requirements for bulwark on the dock"
        en_canon = canonicalize_condensed_query(orig, en_raw)

        call_count = 0
        def fake_get(q, lang, mode):
            nonlocal call_count
            if call_count == 0:
                return None
            return en_canon

        with patch("src.llm.chain._condense_cache_get", side_effect=fake_get), \
             patch("src.llm.chain._condense_cache_put"), \
             patch("src.llm.chain.chat") as mock_chat, \
             patch("src.llm.chain._clean_one_liner") as mock_clean:
            mock_chat.return_value = en_raw
            mock_clean.return_value = en_raw

            r_miss = _translate_condense(
                orig, [], temperature=0.0, mode="default", lang="id"
            )
            call_count = 1
            r_hit = _translate_condense(
                orig, [], temperature=0.0, mode="default", lang="id"
            )
            assert r_miss == r_hit
            assert "forward deck" in r_miss
            assert "bulwark" in r_miss
            assert "bilge keel" not in r_miss

    def test_cache_hit_bad_en_query_stale_with_version_bump(self):
        """v2 cached rows are misses under v3 (query kept 'geladak depan' pure)."""
        q = "Apa tujuan pemasangan breakwater di geladak depan?"
        norm = _normalize_for_cache(q)
        old_hash = hashlib.sha256(
            f"2|id|default|{norm}".encode()
        ).hexdigest()
        current_hash = _cache_hash("id", "default", _normalize_for_cache(q))
        assert old_hash != current_hash

    def test_cache_hit_identical_to_miss(self):
        """Cache put stores same value that miss returns."""
        en_query = "what is the purpose of installing a breakwater on the forward deck"
        with patch("src.llm.chain._condense_cache_get") as mock_get, \
             patch("src.llm.chain._condense_cache_put") as mock_put:
            mock_get.return_value = None

            with patch("src.llm.chain.chat") as mock_chat, \
                 patch("src.llm.chain._clean_one_liner") as mock_clean:
                mock_chat.return_value = en_query
                mock_clean.return_value = en_query

                result_miss = _translate_condense(
                    "Apa tujuan pemasangan breakwater di geladak depan?",
                    [], temperature=0.0, mode="default", lang="id"
                )
                stored = mock_put.call_args[0][3]
                assert result_miss == en_query
                assert stored == en_query

    def test_idempotent_condense_cache(self):
        """Double call with same query: first miss stores, second hit returns same."""
        en_query = "what is the purpose of installing a breakwater on the forward deck"
        call_count = 0

        def fake_get(q, lang, mode):
            nonlocal call_count
            if call_count == 0:
                return None
            return en_query

        captured = {}

        def fake_put(q, lang, mode, eq):
            captured["stored"] = eq

        with patch("src.llm.chain._condense_cache_get", side_effect=fake_get), \
             patch("src.llm.chain._condense_cache_put", side_effect=fake_put), \
             patch("src.llm.chain.chat") as mock_chat, \
             patch("src.llm.chain._clean_one_liner") as mock_clean:
            mock_chat.return_value = en_query
            mock_clean.return_value = en_query

            r1 = _translate_condense(
                "Apa tujuan pemasangan breakwater di geladak depan?",
                [], temperature=0.0, mode="default", lang="id"
            )
            call_count = 1
            r2 = _translate_condense(
                "Apa tujuan pemasangan breakwater di geladak depan?",
                [], temperature=0.0, mode="default", lang="id"
            )
            assert r1 == r2
            assert "forward deck" in r1
            assert "forward deck" in r2

    def test_cache_failure_graceful_degrade(self):
        """Supabase error in _condense_cache_get is caught; LLM is called."""
        with patch("src.llm.chain.get_client") as mock_get_client, \
             patch("src.llm.chain._condense_cache_put") as mock_put, \
             patch("src.llm.chain.chat") as mock_chat, \
             patch("src.llm.chain._clean_one_liner") as mock_clean:
            mock_get_client.side_effect = RuntimeError("connection lost")
            mock_chat.return_value = "live result from LLM"
            mock_clean.return_value = "live result from LLM"

            result = _translate_condense(
                "test query", [], temperature=0.0, mode="default", lang="id"
            )
            assert result == "live result from LLM"
            mock_chat.assert_called_once()

    def test_non_deck_query_unchanged_1(self):
        """Technical query without geladak depan → canonicalization is a no-op."""
        r = canonicalize_condensed_query(
            "berapa ketebalan minimum pelat lambung untuk kapal tanker?",
            "what is the minimum shell plate thickness for tanker ships"
        )
        assert "forward deck" not in r
        assert "thickness" in r

    def test_non_deck_query_unchanged_2(self):
        """Another non-deck technical query stays unchanged."""
        r = canonicalize_condensed_query(
            "apa persyaratan sistem bilga untuk kapal penumpang?",
            "what are the bilge system requirements for passenger ships"
        )
        assert "forward deck" not in r
        assert "bilge" in r
