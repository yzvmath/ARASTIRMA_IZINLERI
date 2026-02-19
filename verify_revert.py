import requests
import sqlite3

BASE_URL = "http://127.0.0.1:5000"
TEST_ID = 5 # Used in previous tests, currently 'onaylandi'

def check_revert():
    print(f"Testing Revert for ID {TEST_ID}...")
    
    # 1. Verify it is initially 'onaylandi'
    # We can check via Tamamlananlar page or DB
    
    # 2. Call Revert
    print("Sending Revert request...")
    resp = requests.post(f"{BASE_URL}/basvuru/{TEST_ID}/geri-al")
    
    # 3. Verify Status changed to 'okul_secimi'
    # Check DB
    conn = sqlite3.connect("degerlendirme.db")
    c = conn.cursor()
    c.execute("SELECT degerlendirme_durumu FROM basvuru WHERE id=?", (TEST_ID,))
    row = c.fetchone()
    conn.close()
    
    status = row[0]
    print(f"New Status: {status}")
    
    if status == "okul_secimi":
        print("PASS: Application reverted successfully.")
    else:
        print(f"FAIL: Expected 'okul_secimi', got '{status}'")

    # 4. Cleanup: Complete it again so it doesn't stay in pending for user (optional, or maybe user wants checking it)
    # Let's revert it back to completed to leave state clean? 
    # Or leave it reverted so I can verify on dashboard? 
    # Leaving it reverted allows me to check if it re-appears on dashboard.
    
    # Check if it appears on dashboard again
    dash = requests.get(BASE_URL).text
    if "bi-building-check" in dash: # Icon for okul_secimi
        print("PASS: Application reappeared on Dashboard.")
    else:
        print("FAIL: Application not found on Dashboard.")

if __name__ == "__main__":
    check_revert()
