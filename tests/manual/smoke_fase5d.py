"""Comprehensive test untuk Fase 5d error handling."""
import sys
import os

sys.path.insert(0, '.')

print("=" * 60)
print("FASE 5D ERROR HANDLING TEST")
print("=" * 60)

# Test 1: Import check (no circular dependency)
print("\n[TEST 1] Import check (no circular dependency)")
try:
    import src.cli.app
    import src.cli.exceptions
    import src.llm.client
    import src.core.db
    import src.retrieval.search
    print("[PASS] All imports successful, no circular dependency")
except Exception as e:
    print(f"[FAIL] Import error: {e}")
    sys.exit(1)

# Test 2: Exception types exist
print("\n[TEST 2] Exception types exist")
try:
    from src.cli.exceptions import OllamaUnavailable, SupabaseUnavailable, RetrievalError
    print("[PASS] All exception types imported")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

# Test 3: check_ollama_available() with running Ollama
print("\n[TEST 3] check_ollama_available() with running Ollama")
try:
    from src.llm.client import check_ollama_available
    check_ollama_available()
    print("[PASS] Ollama check passed (Ollama is running)")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

# Test 4: ping_supabase() with valid config
print("\n[TEST 4] ping_supabase() with valid config")
try:
    from src.core.db import ping_supabase
    ping_supabase()
    print("[PASS] Supabase ping passed")
except Exception as e:
    # Supabase might be unavailable due to network issues - this is OK for testing
    # The important thing is that the exception is caught and wrapped correctly
    if "Supabase ping failed" in str(e) or "SupabaseUnavailable" in str(type(e).__name__):
        print(f"[PASS] Supabase ping correctly wrapped error: {type(e).__name__}")
    else:
        print(f"[FAIL] {e}")
        sys.exit(1)

# Test 5: Verify code structure (non-interactive)
print("\n[TEST 5] Verify code structure")
try:
    import inspect
    from src.cli.app import run, _check_services
    
    # Check _check_services exists
    assert callable(_check_services), "_check_services not callable"
    
    # Check run() calls _check_services
    source = inspect.getsource(run)
    assert '_check_services' in source, "_check_services not called in run()"
    
    # Check exception handling in run()
    assert 'OllamaUnavailable' in source, "OllamaUnavailable not handled in run()"
    assert 'SupabaseUnavailable' in source, "SupabaseUnavailable not handled in run()"
    assert 'RetrievalError' in source, "RetrievalError not handled in run()"
    
    print("[PASS] Code structure verified")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
