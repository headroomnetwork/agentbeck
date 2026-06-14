import requests
import sys
import time

BASE_URL = "https://agentbeck.bot"

def print_result(name, success, info=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {name} {info}")
    if not success:
        sys.exit(1)

def test_health():
    r = requests.get(f"{BASE_URL}/health")
    print_result("test_health", r.status_code == 200 and r.json().get("ok"))

def test_stats():
    r = requests.get(f"{BASE_URL}/stats")
    print_result("test_stats", r.status_code == 200 and "reports" in r.json())

def test_good_citizen_lifecycle():
    # 1. Post a new fix
    payload = {
        "error": "Uniquely generated error " + str(time.time()),
        "fix": "Run npm cache clean --force",
        "environment": "Node.js",
        "tags": "npm cache",
        "source": "integration_test"
    }
    r = requests.post(f"{BASE_URL}/reports", json=payload)
    if r.status_code != 201:
        print_result("lifecycle_create", False, f"HTTP {r.status_code}")
    
    data = r.json()
    rid = data["report"]["id"]
    token = data["deletion_token"]
    
    # 2. Confirm it
    r2 = requests.post(f"{BASE_URL}/reports/{rid}/worked")
    if r2.status_code != 200 or r2.json()["report"]["confirmations"] != 1:
        print_result("lifecycle_confirm", False)
        
    # 3. Read it via search
    r3 = requests.get(f"{BASE_URL}/search?q=npm cache clean")
    found = any(res["report"]["id"] == rid for res in r3.json().get("results", []))
    if not found:
        print_result("lifecycle_search", False, "Could not find newly created report")
        
    # 4. Delete it
    r4 = requests.delete(f"{BASE_URL}/reports/{rid}", headers={"X-Deletion-Token": token})
    if r4.status_code != 200 or not r4.json().get("deleted"):
        print_result("lifecycle_delete", False)
        
    print_result("test_good_citizen_lifecycle", True)

def test_duplicate_rejection():
    payload = {
        "error": "Duplicate error target " + str(time.time()),
        "fix": "Just a duplicate fix",
        "environment": "Test",
        "tags": "duplicate",
        "source": "integration_test"
    }
    # Create first
    r1 = requests.post(f"{BASE_URL}/reports", json=payload)
    token = r1.json()["deletion_token"]
    rid = r1.json()["report"]["id"]
    
    # Try creating EXACT SAME error
    payload2 = payload.copy()
    payload2["fix"] = "A slightly different fix"
    r2 = requests.post(f"{BASE_URL}/reports", json=payload2)
    
    # Should return 200 OK, is_duplicate True, and confirmations incremented to 1
    if r2.status_code == 200 and r2.json().get("is_duplicate") is True:
        if r2.json()["report"]["confirmations"] == 1:
            print_result("test_duplicate_rejection", True)
        else:
            print_result("test_duplicate_rejection", False, "Confirmations did not increment")
    else:
        print_result("test_duplicate_rejection", False, f"Expected 200, got {r2.status_code}. Data: {r2.text}")
        
    # Cleanup
    requests.delete(f"{BASE_URL}/reports/{rid}", headers={"X-Deletion-Token": token})

def test_malicious_injection_sanitization():
    payload = {
        "error": "My error is <script>alert('xss')</script>",
        "fix": "Run `rm -rf /` and # hashtag",
        "environment": "Hackerland",
        "tags": "xss inject",
        "source": "integration_test"
    }
    r = requests.post(f"{BASE_URL}/reports", json=payload)
    if r.status_code != 201:
        print_result("test_sanitization", False, "Failed to create")
    
    data = r.json()["report"]
    token = r.json()["deletion_token"]
    
    # Check escaping
    if "<script>" in data["error"] or not data["content_warnings"]:
        print_result("test_sanitization", False, f"HTML was not escaped properly: {data['error']}")
    elif "markdown-escaped" not in data["content_warnings"].get("fix", []):
        print_result("test_sanitization", False, "Markdown wasn't escaped")
    else:
        print_result("test_malicious_injection_sanitization", True)
        
    requests.delete(f"{BASE_URL}/reports/{data['id']}", headers={"X-Deletion-Token": token})

def test_secret_rejection():
    payload = {
        "error": "I leaked my openai key",
        "fix": "Here it is: sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890",
        "environment": "Test",
        "tags": "leak",
        "source": "integration_test"
    }
    r = requests.post(f"{BASE_URL}/reports", json=payload)
    if r.status_code == 422 and "Potential secret pattern detected" in r.text:
        print_result("test_secret_rejection", True)
    else:
        print_result("test_secret_rejection", False, f"Failed to reject API key, got {r.status_code}")

def test_rate_limit():
    # Rapid fire 50 requests
    hits = 0
    blocked = False
    for i in range(65):
        r = requests.get(f"{BASE_URL}/search?q=spam{i}")
        if r.status_code == 429:
            blocked = True
            break
        hits += 1
    
    if blocked:
        print_result("test_rate_limit", True, f"Blocked after {hits} requests")
    else:
        print_result("test_rate_limit", False, "Failed to rate limit 65 requests")

def test_audit_chain():
    r = requests.get(f"{BASE_URL}/audit/verify")
    if r.status_code == 200 and r.json().get("ok") is True:
        print_result("test_audit_chain", True)
    else:
        print_result("test_audit_chain", False, "Audit chain is broken!")

if __name__ == "__main__":
    print(f"Starting scenario tests against {BASE_URL}...")
    test_health()
    test_stats()
    test_audit_chain()
    test_good_citizen_lifecycle()
    test_duplicate_rejection()
    test_malicious_injection_sanitization()
    test_secret_rejection()
    test_rate_limit()
    print("\n🎉 All scenario tests passed successfully!")
