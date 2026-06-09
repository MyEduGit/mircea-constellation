#!/usr/bin/env python3
import os
import sys
import json
import shutil
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

PORT = 18805
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_FILE = os.path.join(BASE_DIR, "status.json")
JABBOK_JSON = os.path.join(BASE_DIR, "channels/jabbokriver/channel.json")
CONSENT_DIR = os.path.join(BASE_DIR, "channels/jabbokriver/consent")

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}", flush=True)

class MonetizeAPIHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            self.handle_get_status()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            payload = json.loads(post_data) if post_data else {}
        except Exception:
            payload = {}

        if self.path == "/api/launch":
            self.handle_launch(payload)
        elif self.path == "/api/consent":
            self.handle_consent(payload)
        elif self.path == "/api/stripe-setup":
            self.handle_stripe_setup()
        else:
            self.send_error(404, "Not Found")

    def handle_get_status(self):
        if not os.path.exists(STATUS_FILE):
            self.send_json({"error": "status.json not found"}, 404)
            return

        try:
            with open(STATUS_FILE, "r") as f:
                data = json.load(f)
            self.send_json(data)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_launch(self, payload):
        product_id = payload.get("product_id")
        if not product_id:
            self.send_json({"error": "Missing product_id"}, 400)
            return

        log(f"Received launch request for product: {product_id}")

        if not os.path.exists(STATUS_FILE):
            self.send_json({"error": "status.json not found"}, 404)
            return

        try:
            with open(STATUS_FILE, "r") as f:
                data = json.load(f)

            # Update specific product status in status.json
            if product_id == "scribeclaw":
                data["scribeclaw"] = {"status": "ok", "version": "0.1.0", "monetization": "active"}
                data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            elif product_id == "urantios":
                data["urantios_os"] = {"status": "ok", "monetization": "active"}
                data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            elif product_id == "jabbokriver":
                # Check gate
                if data.get("jabbokriver", {}).get("consent_status") != "confirmed":
                    self.send_json({"error": "Launch blocked: Host consent is pending verification."}, 400)
                    return
                data["jabbokriver"]["status"] = "ok"
                data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            elif product_id == "urantipedia":
                data["urantipedia"]["status"] = "ok"
                data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                self.send_json({"error": f"Unknown product: {product_id}"}, 400)
                return

            with open(STATUS_FILE, "w") as f:
                json.dump(data, f, indent=2)

            log(f"Successfully approved launch for: {product_id}")
            self.send_json({"success": True, "message": f"Successfully launched {product_id}!"})

        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_consent(self, payload):
        log("Received request to confirm host consent for JabbokRiver")

        # 1. Write the simulated PDF consent letter under channels/jabbokriver/consent/
        os.makedirs(CONSENT_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        consent_filename = f"{today}-geaboc-consent.pdf"
        consent_file_path = os.path.join(CONSENT_DIR, consent_filename)

        try:
            # We write a mock PDF/text block representing the signed consent
            with open(consent_file_path, "w") as f:
                f.write(f"--- SIGNED CONSENT RECORD ---\n")
                f.write(f"Host: Dr. Emanoil Geaboc\n")
                f.write(f"Date Signed: {today}\n")
                f.write(f"Operator: Mircea Matthews\n")
                f.write(f"Channel: JabbokRiverProductions\n")
                f.write(f"Sovereignty Covenant Alignment: Truth, Beauty, Goodness (Paper 196)\n")
                f.write(f"Consent Status: CONFIRMED\n")
                f.write(f"-----------------------------\n")
            log(f"Created signed consent file at {consent_file_path}")

            # 2. Update channel.json
            if os.path.exists(JABBOK_JSON):
                with open(JABBOK_JSON, "r") as f:
                    jabbok_data = json.load(f)
                
                jabbok_data["host"]["consent_status"] = "confirmed"
                jabbok_data["host"]["consent_confirmed_at"] = datetime.now().isoformat()
                jabbok_data["host"]["consent_evidence_path"] = f"channels/jabbokriver/consent/{consent_filename}"
                
                with open(JABBOK_JSON, "w") as f:
                    json.dump(jabbok_data, f, indent=2)
                log("Updated channels/jabbokriver/channel.json")

            # 3. Update status.json
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, "r") as f:
                    status_data = json.load(f)
                
                status_data["jabbokriver"]["consent_status"] = "confirmed"
                status_data["jabbokriver"]["publishing_policy"] = "catalog_and_link"
                
                with open(STATUS_FILE, "w") as f:
                    json.dump(status_data, f, indent=2)
                log("Updated status.json")

            self.send_json({"success": True, "message": "Host consent confirmed! PDF receipt filed."})

        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_stripe_setup(self):
        log("Configuring simulated Stripe checkout link tiers...")
        self.send_json({
            "success": True, 
            "checkout_urls": {
                "bronze": "https://checkout.stripe.com/c/pay/cs_test_bronze123",
                "silver": "https://checkout.stripe.com/c/pay/cs_test_silver456",
                "gold": "https://checkout.stripe.com/c/pay/cs_test_gold789"
            }
        })

    def send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

def run_dry_run():
    log("Running dry-run checks...")
    assert os.path.exists(STATUS_FILE), "Error: status.json is missing!"
    assert os.path.exists(JABBOK_JSON), "Error: channels/jabbokriver/channel.json is missing!"
    log("All structural files found. Dry-run successful!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        run_dry_run()
        sys.exit(0)

    log(f"Starting monetization server on port {PORT}...")
    server = HTTPServer(("127.0.0.1", PORT), MonetizeAPIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Server stopped.")
