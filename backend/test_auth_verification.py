import urllib.request
import urllib.error
import json

base_url = "http://127.0.0.1:8017"

print("--- Testing POST /api/auth/admin/login with Admin / admin@123 ---")
data = json.dumps({"username": "Admin", "password": "admin@123"}).encode('utf-8')
req = urllib.request.Request(
    f"{base_url}/api/auth/admin/login",
    data=data,
    headers={
        "Content-Type": "application/json",
        "Origin": "http://localhost:3000"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        print("Status:", resp.status)
        print("CORS Allow-Origin:", resp.headers.get("access-control-allow-origin"))
        print("CORS Allow-Credentials:", resp.headers.get("access-control-allow-credentials"))
        print("Body:", resp.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP Error Status:", e.code)
    print("CORS Allow-Origin:", e.headers.get("access-control-allow-origin"))
    print("CORS Allow-Credentials:", e.headers.get("access-control-allow-credentials"))
    print("Body:", e.read().decode())

print("\n--- Testing Invalid Credentials ---")
data_bad = json.dumps({"username": "superadmin", "password": "wrongpassword"}).encode('utf-8')
req_bad = urllib.request.Request(
    f"{base_url}/api/auth/admin/login",
    data=data_bad,
    headers={
        "Content-Type": "application/json",
        "Origin": "http://localhost:3000"
    },
    method="POST"
)
try:
    with urllib.request.urlopen(req_bad) as resp:
        print("Status:", resp.status)
except urllib.error.HTTPError as e:
    print("HTTP Error Status:", e.code)
    print("CORS Allow-Origin:", e.headers.get("access-control-allow-origin"))
    print("CORS Allow-Credentials:", e.headers.get("access-control-allow-credentials"))
    print("Body:", e.read().decode())
