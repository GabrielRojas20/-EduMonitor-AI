import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["MOCK_SYNC_SECONDS"] = "0.3"  # sincronizaciones simuladas rápidas

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.store import store  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state():
    store.reset()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _token(client, email: str) -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "Prueba123!"})
    assert r.status_code == 200, r.text
    return r.json()["accessToken"]


@pytest.fixture
def teacher(client):
    """Cabeceras del docente 1 (dueño de los cursos 2 y 3)."""
    return {"Authorization": f"Bearer {_token(client, 'docente1@example.com')}"}


@pytest.fixture
def teacher2(client):
    """Cabeceras del docente 2 (dueño del curso 4)."""
    return {"Authorization": f"Bearer {_token(client, 'docente2@example.com')}"}
