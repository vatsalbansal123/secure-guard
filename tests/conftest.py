"""Test setup: isolate the key store and avoid any real Azure calls.

Runs before the app is imported so the env is in place when modules initialize.
"""

import os
import sys
import tempfile

# Make backend/ importable (main, auth, models, agent).
BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, BACKEND)

# Point the API-key store at a throwaway SQLite file.
_DB = os.path.join(tempfile.gettempdir(), "secureguard_test.db")
if os.path.exists(_DB):
    os.remove(_DB)
os.environ["SECUREGUARD_DB"] = _DB

# Dummy Azure creds so AzureChatOpenAI instantiates at import time without
# real secrets. The graph is monkeypatched in tests, so no network call is made.
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test-key")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT", "test-deployment")
