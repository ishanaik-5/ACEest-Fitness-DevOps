
import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    test_database = tmp_path / "test_aceest.db"

    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "DATABASE": str(test_database),
    })

    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


def test_existing_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "healthy"
    assert response.json["application"] == "ACEest Fitness & Gym"


def test_version_endpoint(client):
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json["application"] == "ACEest Fitness & Gym"
    assert isinstance(response.json["version"], str)
    assert response.json["version"]


def test_liveness_endpoint(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json["status"] == "alive"


def test_readiness_endpoint(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json["status"] == "ready"
