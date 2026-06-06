import os
import sys
from pathlib import Path

os.environ["OPENAI_API_KEY"] = ""
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


import pytest


@pytest.fixture(autouse=True)
def reset_store():
    from app import store

    store.store_singleton = None
