import pytest
from fastapi.testclient import TestClient
import os
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
from main import app

@pytest.fixture
def client():
    return TestClient(app)
