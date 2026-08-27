def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "customer-support-rag-backend",
    }
    assert "secret" not in response.text.lower()
    assert "token" not in response.text.lower()
    assert "database" not in response.text.lower()
