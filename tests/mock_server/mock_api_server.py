"""
Mock Cloud AI Server for Smart Trash Bin (Zero-dependency - runs on Python standard library)
========================================================================================
This server simulates the Roboflow Cloud Inference API locally on your PC.
It accepts HTTP POST with JPEG binary image from the ESP32-S3, saves the received image
to disk so you can verify camera quality, and responds with standard JSON predictions.

Usage:
    python mock_api_server.py
Then on ESP32-S3 code, set:
    const char* API_INFERENCE_URL = "http://<YOUR_PC_LOCAL_IP>:5000/predict";
"""

import os
import json
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 5000
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "received_images")
os.makedirs(IMAGE_DIR, exist_ok=True)

CLASSES = [
    {"class": "Recyclable", "confidence": 0.94},
    {"class": "General", "confidence": 0.88},
    {"class": "Wet", "confidence": 0.91},
    {"class": "Hazardous", "confidence": 0.95},
]

class MockApiHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        timestamp = int(time.time())
        img_filename = f"capture_{timestamp}.jpg"
        img_path = os.path.join(IMAGE_DIR, img_filename)

        with open(img_path, "wb") as f:
            f.write(post_data)

        # Pick a prediction or rotate classes
        chosen = random.choice(CLASSES)

        response_payload = {
            "time": 0.045,
            "image": {
                "width": 320,
                "height": 240,
                "bytes_received": content_length,
                "saved_as": img_filename
            },
            "predictions": [
                {
                    "x": 160.0,
                    "y": 120.0,
                    "width": 140.0,
                    "height": 180.0,
                    "confidence": chosen["confidence"],
                    "class": chosen["class"],
                    "class_id": 1
                }
            ]
        }

        response_bytes = json.dumps(response_payload, indent=2).encode('utf-8')

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

        print(f"\n[+] Received Image from ESP32-S3: {content_length} bytes")
        print(f"    Saved to: {img_path}")
        print(f"    AI Predicted: '{chosen['class']}' (Confidence: {chosen['confidence'] * 100:.1f}%)")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""
        <html>
        <head><title>Smart Trash Bin Mock AI Server</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>🤖 Smart Trash Bin - Mock Cloud AI Server (Running)</h2>
            <p>Status: <b>ONLINE</b> on port {PORT}</p>
            <p>ESP32-S3 URL: <code>http://&lt;YOUR_PC_IP&gt;:{PORT}/predict</code></p>
            <h3>Images captured by ESP32:</h3>
            <p>Check the <code>received_images/</code> folder in this directory.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

def run():
    server = HTTPServer(('0.0.0.0', PORT), MockApiHandler)
    print(f"===========================================================")
    print(f"  Smart Trash Bin - Mock AI Server Running on Port {PORT}")
    print(f"  Endpoint for ESP32-S3: http://<YOUR_PC_IP>:{PORT}/predict")
    print(f"  Images saved to: {IMAGE_DIR}")
    print(f"===========================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")

if __name__ == "__main__":
    run()
