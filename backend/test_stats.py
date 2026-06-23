import requests
import json

BASE = "http://localhost:8000/api"

print("=== Testing backend connectivity ===")
try:
    r = requests.get(f"{BASE}/health", timeout=5)
    print(f"Health: {r.status_code} -> {r.json()}")
except Exception as e:
    print(f"Health check FAILED: {e}")
    exit(1)

print("\n=== Testing admin login ===")
try:
    r = requests.post(f"{BASE}/auth/admin/login", json={"username": "superadmin", "password": "#123321#"}, timeout=5)
    print(f"Login: {r.status_code} -> {r.text[:200]}")
    if r.status_code != 200:
        print("Login failed, stopping.")
        exit(1)
    token = r.json().get("token")
    print(f"Token obtained: {bool(token)}")
except Exception as e:
    print(f"Login FAILED: {e}")
    exit(1)

print("\n=== Testing /stats endpoint ===")
try:
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE}/stats", headers=headers, timeout=10)
    print(f"Stats: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print(f"Stats FAILED: {e}")
