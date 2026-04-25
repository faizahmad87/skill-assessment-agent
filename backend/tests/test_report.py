def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_report_not_found(client):
    res = client.get("/api/report/nonexistent-session-id")
    assert res.status_code == 404

def test_analyze_missing_body(client):
    res = client.post("/api/analyze", json={})
    assert res.status_code == 422
