import sys
import io
import time
import serial
import serial.tools.list_ports

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("  ESP32-S3 REAL-TIME DIAGNOSTIC MONITOR")
print("=" * 60)
print("Waiting for ESP32 USB connection...")

target_port = None
t_wait_start = time.time()
while not target_port and time.time() - t_wait_start < 60:
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "COM" in p.device and p.device not in ["COM3", "COM4"]:
            target_port = p.device
            break
    if not target_port:
        time.sleep(0.5)

if not target_port:
    print("[TIMEOUT] Did not detect board within 60s.")
    sys.exit(0)

print(f"\n[PORT FOUND] Detected board on {target_port}!")
print(f"Opening Serial at 921600 baud...")

try:
    ser = serial.Serial(target_port, 921600, timeout=1)
    print("[CONNECTED] Serial opened! Listening to ESP32 logs...\n")
    print("-" * 60)
    
    t_end = time.time() + 90
    while time.time() < t_end:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"[{time.strftime('%H:%M:%S')}] {line}", flush=True)
        time.sleep(0.01)
    ser.close()
except Exception as e:
    print(f"[ERROR] Serial exception: {e}")

print("\nFinished Serial Monitoring.")
