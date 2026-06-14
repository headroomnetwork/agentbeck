import requests
import sys
import os

BASE_URL = os.environ.get("AGENTBECK_TEST_URL", "http://127.0.0.1:8000")

def test_health():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    print("✓ Health check passed")

def test_stats():
    r = requests.get(f"{BASE_URL}/stats")
    assert r.status_code == 200
    assert r.json()["reports"] >= 200
    print("✓ Stats check passed")

def test_search():
    r = requests.get(f"{BASE_URL}/search?q=database")
    assert r.status_code == 200
    data = r.json()
    assert data["envelope"] == "agentbeck.inert_data"
    assert len(data["results"]) > 0
    print("✓ Search check passed")

def test_lifecycle():
    # Create
    r = requests.post(f"{BASE_URL}/reports", json={
        "error": "Live Smoke Test Error",
        "fix": "Live Smoke Test Fix",
        "environment": "Production",
        "tags": "test live smoke",
        "source": "smoke_test"
    })
    assert r.status_code == 201
    data = r.json()
    rid = data["report"]["id"]
    token = data["deletion_token"]
    
    # Confirm
    r2 = requests.post(f"{BASE_URL}/reports/{rid}/worked")
    assert r2.status_code == 200
    assert r2.json()["report"]["confirmations"] == 1
    
    # Delete
    r3 = requests.delete(f"{BASE_URL}/reports/{rid}", headers={"X-Deletion-Token": token})
    assert r3.status_code == 200
    assert r3.json()["deleted"] is True
    print("✓ Lifecycle (Create -> Confirm -> Delete) passed")

if __name__ == "__main__":
    try:
        print(f"Running smoke tests against {BASE_URL}...")
        test_health()
        test_stats()
        test_search()
        test_lifecycle()
        print("\nAll live smoke tests passed successfully!")
    except Exception as e:
        print(f"Live smoke test failed: {e}")
        sys.exit(1)
