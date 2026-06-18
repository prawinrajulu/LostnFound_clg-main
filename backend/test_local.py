import urllib.request
import json

hosts = ["localhost", "127.0.0.1", "[::1]"]
ports = [8000, 8001]

for port in ports:
    for host in hosts:
        url = f"http://{host}:{port}/api/setup/create-admin"
        print(f"Trying {url}...")
        try:
            req = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode('utf-8')
                print(f"SUCCESS on {url}: {html}")
        except Exception as e:
            print(f"FAILED on {url}: {e}")
