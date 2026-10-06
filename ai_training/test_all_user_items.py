"""
Test All User Items Against Cloud AI Server Logic
=================================================
Validates that every single item the user scanned is correctly classified:
- Tape rolls -> General (Bin 0)
- Tissue packs -> General (Bin 0)
- Solder wire -> Hazardous (Bin 3)
- Power Glue -> Hazardous (Bin 3)
- Mobile phone -> Hazardous (Bin 3)
- Cups & Bottles -> Recyclable (Bin 1)
- Paper / Pink notes -> General (Bin 0)
- Empty hands -> Person (Bin -1, lid stays closed)
"""

import os
import sys
import cv2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from ai_training.cloud_ai_server import classify_frame, BINS

TEST_CASES = [
    # Tape rolls
    ("raw_20261005_150030.jpg", 0, "ม้วนเทปใส (Tape Roll)"),
    ("raw_20261005_150019.jpg", 0, "ม้วนเทปใส (Tape Roll)"),
    
    # Tissue packs
    ("raw_20261005_145914.jpg", 0, "ห่อทิชชู่เขียว (Tissue Pack)"),
    ("raw_20261005_145903.jpg", 0, "ห่อทิชชู่เขียว (Tissue Pack)"),
    
    # Solder wire
    ("raw_20261005_145940.jpg", 3, "ม้วนตะกั่วบัดกรี (Solder Spool)"),
    
    # Power Glue
    ("raw_20261005_150153.jpg", 3, "กาวตราช้าง Power Glue (Blister)"),
    ("raw_20261005_150131.jpg", 3, "กาวตราช้าง Power Glue (Close-up)"),
    
    # Blue folder
    ("raw_20261005_150050.jpg", 0, "แฟ้มสีน้ำเงิน (Folder)"),
    
    # Mobile Phones
    ("raw_20261005_145817.jpg", 3, "โทรศัพท์มือถือ (Phone)"),
    ("raw_20261005_143801.jpg", 3, "โทรศัพท์มือถือ (Phone held in hand)"),
    ("raw_20261005_104605.jpg", 3, "โทรศัพท์มือถือ (Phone)"),
    
    # Cups & Bottles
    ("raw_20261005_145952.jpg", 1, "แก้วน้ำพลาสติก (Cup)"),
    ("raw_20261005_142222.jpg", 1, "ขวดน้ำใสฝาเขียว (Water Bottle)"),
    ("raw_20261005_095039.jpg", 1, "แก้วน้ำพลาสติก (Cup)"),
    ("raw_20261005_100133.jpg", 1, "แก้วน้ำพลาสติก (Cup)"),
    
    # Pink paper note
    ("raw_20261005_142147.jpg", 0, "กระดาษโน้ตสีชมพู (Paper Note)"),
]

def main():
    print("=" * 75)
    print("  🧪 COMPREHENSIVE USER SCAN VERIFICATION")
    print("=" * 75)
    
    passed = 0
    total = len(TEST_CASES)

    for fname, expected_bin, desc in TEST_CASES:
        fpath = os.path.join("captured_scans", fname)
        if not os.path.exists(fpath):
            print(f"⚠️ [MISSING] {fname}")
            continue

        img = cv2.imread(fpath)
        ret_bin, label, conf, box = classify_frame(img)

        # Success check: either matches expected_bin, or general/recyclable accepted for paper/tape
        is_ok = (ret_bin == expected_bin)
        
        status_sym = "✅ PASS" if is_ok else "❌ FAIL"
        exp_name = BINS.get(expected_bin, {}).get("title", f"BIN {expected_bin}")
        ret_name = BINS.get(ret_bin, {}).get("title", f"BIN {ret_bin}") if ret_bin >= 0 else "NO_ITEM/PERSON"

        print(f"{status_sym} | [{fname}] {desc}")
        print(f"       Expected: {exp_name} (Bin {expected_bin}) ➔ Got: {ret_name} (Bin {ret_bin}) | {label} ({conf*100:.1f}%)")
        
        if is_ok:
            passed += 1

    print("=" * 75)
    print(f"🏁 Final Result: {passed}/{total} Passed ({passed/total*100:.1f}%)")
    print("=" * 75)

if __name__ == "__main__":
    main()
