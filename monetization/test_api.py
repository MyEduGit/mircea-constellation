#!/usr/bin/env python3
import os
import time
import json
import urllib.request
import subprocess

PORT = 18805
API_URL = f"http://127.0.0.1:{PORT}"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_FILE = os.path.join(BASE_DIR, "status.json")
JABBOK_JSON = os.path.join(BASE_DIR, "channels/jabbokriver/channel.json")
CONSENT_DIR = os.path.join(BASE_DIR, "channels/jabbokriver/consent")

def test_api():
    print("🚀 Spawning monetization server...")
    server_path = os.path.join(BASE_DIR, "monetization", "monetize.py")
    proc = subprocess.Popen([sys.executable, server_path])
    time.sleep(1.5)  # Wait for server to start

    try:
        # Test 1: GET status
        print("Test 1: GET /api/status")
        req = urllib.request.Request(f"{API_URL}/api/status")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            assert "jabbokriver" in data, "Failed: jabbokriver status key missing"
            print("✓ GET /api/status passed")

        # Test 2: POST consent
        print("Test 2: POST /api/consent")
        req = urllib.request.Request(
            f"{API_URL}/api/consent",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            assert res.get("success"), "Failed to confirm consent"
            
            # Verify file updates
            with open(JABBOK_JSON, "r") as f:
                j_data = json.load(f)
            assert j_data["host"]["consent_status"] == "confirmed", "jabbok channel.json not updated"

            with open(STATUS_FILE, "r") as f:
                s_data = json.load(f)
            assert s_data["jabbokriver"]["consent_status"] == "confirmed", "status.json consent not updated"
            
            print("✓ POST /api/consent passed")

        # Test 3: POST launch scribeclaw
        print("Test 3: POST /api/launch (scribeclaw)")
        req = urllib.request.Request(
            f"{API_URL}/api/launch",
            data=json.dumps({"product_id": "scribeclaw"}).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            assert res.get("success"), "Failed to launch scribeclaw"

            with open(STATUS_FILE, "r") as f:
                s_data = json.load(f)
            assert s_data.get("scribeclaw", {}).get("monetization") == "active", "status.json scribeclaw not updated"

            print("✓ POST /api/launch passed")

        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")

    finally:
        print("Stopping monetization server...")
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    import sys
    test_api()
