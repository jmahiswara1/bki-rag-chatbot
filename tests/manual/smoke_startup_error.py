"""Test script untuk Fase 5d error handling."""
import sys
import os

# Set environment variable sebelum import
os.environ['OLLAMA_HOST'] = 'http://localhost:9999'

sys.path.insert(0, '.')

# Force reload config untuk pick up new env var
if 'src.core.config' in sys.modules:
    del sys.modules['src.core.config']

from src.cli.app import run

print("Testing startup with invalid OLLAMA_HOST...")
try:
    run(['--mode', 'default'])
    print('ERROR: Should have exited with code 2')
    sys.exit(1)
except SystemExit as e:
    print(f'\nExit code: {e.code}')
    if e.code == 2:
        print('SUCCESS: Exited with code 2 as expected')
        sys.exit(0)
    else:
        print(f'ERROR: Wrong exit code: {e.code}')
        sys.exit(1)
