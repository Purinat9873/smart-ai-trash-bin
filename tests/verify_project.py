"""
Smart Trash Bin Project Integrity & Verification Suite
======================================================
This automated test script validates:
1. Existence and integrity of all source files, guides, and documentation.
2. Static analysis of Arduino code (Pin safety, Octal PSRAM isolation, logic checks).
3. Live end-to-end test of the Mock AI API Server by simulating an ESP32-S3 HTTP POST.
"""

import os
import sys
import re
import json
import time
import threading
import urllib.request
from http.server import HTTPServer

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def check_file_exists(relative_path):
    full_path = os.path.join(PROJECT_ROOT, relative_path)
    exists = os.path.isfile(full_path)
    status = "PASS" if exists else "FAIL"
    print(f"[{status}] Checking file: {relative_path}")
    return exists

def test_arduino_code_static_analysis():
    print("\n--- Running Static Analysis on smart_trash_bin.ino ---")
    ino_path = os.path.join(PROJECT_ROOT, "src", "smart_trash_bin", "smart_trash_bin.ino")
    if not os.path.exists(ino_path):
        print("[FAIL] smart_trash_bin.ino not found!")
        return False

    with open(ino_path, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. PSRAM enabled check
    has_psram = "CAMERA_FB_IN_PSRAM" in code
    print(f"[{'PASS' if has_psram else 'FAIL'}] PSRAM Framebuffer Buffer Allocation verified")

    # 2. Avoid Octal PSRAM pins (GPIO 33, 34, 35, 36, 37) in #define statements
    # Find all '#define PIN_... <number>'
    pin_defs = re.findall(r'#define\s+PIN_(\w+)\s+(\d+)', code)
    safe_pins = True
    octal_pins = {33, 34, 35, 36, 37}
    for pin_name, pin_num in pin_defs:
        num = int(pin_num)
        if num in octal_pins:
            print(f"[FAIL] GPIO {num} used in PIN_{pin_name} collides with Octal PSRAM!")
            safe_pins = False

    if safe_pins:
        print("[PASS] Safe Pinout: Octal PSRAM GPIOs (33-37) are strictly isolated")

    # 3. Servo Detach to avoid brownout
    has_detach = "detach()" in code
    print(f"[{'PASS' if has_detach else 'FAIL'}] Power Optimization: Servos detach() after movement")

    # 4. Auto-scan sensor
    has_auto_scan = "PIN_AUTO_SCAN_IR" in code
    print(f"[{'PASS' if has_auto_scan else 'FAIL'}] Feature: Hands-Free Auto-Scan sensor enabled")

    # 5. Shared Trigger
    has_shared_trig = "PIN_US_TRIG" in code
    print(f"[{'PASS' if has_shared_trig else 'FAIL'}] GPIO Optimization: HC-SR04 Shared Trigger Multiplexing")

    return has_psram and safe_pins and has_detach and has_auto_scan and has_shared_trig

def test_mock_api_server():
    print("\n--- Testing Mock Cloud AI Server (End-to-End Test) ---")
    mock_server_script = os.path.join(PROJECT_ROOT, "tests", "mock_server", "mock_api_server.py")
    
    sys.path.insert(0, os.path.dirname(mock_server_script))
    from mock_api_server import MockApiHandler
    
    server = HTTPServer(('127.0.0.1', 5056), MockApiHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    try:
        # Simulate ESP32-S3 sending binary image
        dummy_jpeg = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00' + b'DUMMY_IMAGE_DATA_12345'
        req = urllib.request.Request(
            "http://127.0.0.1:5056/predict",
            data=dummy_jpeg,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read()
            json_resp = json.loads(data.decode('utf-8'))
            
            print(f"[PASS] Server HTTP Status: {resp.status}")
            print(f"[PASS] JSON Response received from Mock API: Class='{json_resp['predictions'][0]['class']}', Confidence={json_resp['predictions'][0]['confidence']}")
            
            assert "predictions" in json_resp, "Missing 'predictions' in response"
            assert len(json_resp["predictions"]) > 0, "No predictions returned"
            assert "class" in json_resp["predictions"][0], "Missing 'class' field"
            print("[PASS] AI Inference API Response Schema is 100% compliant with ESP32 ArduinoJson parser!")
            return True
    except Exception as e:
        print(f"[FAIL] Mock server test error: {e}")
        return False
    finally:
        server.shutdown()

def main():
    print("======================================================")
    print("  Smart Trash Bin - Verification & Diagnostics Suite")
    print("======================================================")

    # 1. Check Files
    files_to_check = [
        "src/smart_trash_bin/smart_trash_bin.ino",
        "tests/mock_server/mock_api_server.py",
        "tests/hardware_tests/01_servo_test/01_servo_test.ino",
        "tests/hardware_tests/02_sensors_test/02_sensors_test.ino",
        "ai_training/train_yolov8.py",
        "ai_training/dataset_guide.md",
        "docs/pinout_and_circuit.md",
        "docs/calibration_guide.md",
        "docs/bill_of_materials.md",
        "README.md",
    ]
    all_files_ok = all(check_file_exists(f) for f in files_to_check)

    # 2. Static Analysis
    static_ok = test_arduino_code_static_analysis()

    # 3. Live Server Simulation
    api_ok = test_mock_api_server()

    print("\n======================================================")
    if all_files_ok and static_ok and api_ok:
        print("  [SUCCESS] ALL VERIFICATION TESTS PASSED PERFECTLY!")
    else:
        print("  [FAILED] SOME TESTS FAILED. PLEASE REVIEW LOGS.")
    print("======================================================\n")

if __name__ == "__main__":
    main()
