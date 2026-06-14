"""Test script sederhana untuk _check_services."""
import sys
import os

# Set environment variable sebelum import
os.environ['OLLAMA_HOST'] = 'http://localhost:9999'

sys.path.insert(0, '.')

# Force reload config untuk pick up new env var
if 'src.core.config' in sys.modules:
    del sys.modules['src.core.config']

from rich.console import Console
from src.cli.app import _check_services

console = Console()
print("Testing _check_services with invalid OLLAMA_HOST...")
result = _check_services(console)
print(f"\n_check_services returned: {result}")
if not result:
    print("SUCCESS: _check_services correctly detected failure")
else:
    print("ERROR: _check_services should have returned False")
