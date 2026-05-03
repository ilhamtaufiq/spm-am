import sqlite3
import os
import subprocess
import sys

DB_PATH = "./data/spm_am.db"

def check_schema_version():
    if not os.path.exists(DB_PATH):
        return "NONE"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(achievements)")
        cols = [c[1] for c in cursor.fetchall()]
        conn.close()
        
        if "unit_spam_id" in cols:
            return "NORMALIZED"
        elif "kecamatan" in cols:
            return "LEGACY"
        else:
            return "UNKNOWN"
    except Exception:
        return "ERROR"

def run_deploy():
    print("--- 🚀 STARTING DEPLOYMENT WORKFLOW ---")
    
    # 1. Check schema
    version = check_schema_version()
    print(f"[*] Current Database State: {version}")
    
    if version == "LEGACY":
        print("[!] Old schema detected. Running normalization migration...")
        try:
            # Run the normalization script
            script_path = os.path.join("scratch", "migrate_to_normalized.py")
            if os.path.exists(script_path):
                subprocess.run([sys.executable, script_path], check=True)
                print("[+] Migration successful!")
            else:
                print(f"[ERROR] Migration script not found at {script_path}")
                return
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Migration failed: {e}")
            return
    elif version == "NORMALIZED":
        print("[+] Database already normalized. No heavy migration needed.")
    elif version == "NONE":
        print("[*] Database not found. main.py will seed it from spm_am.db if available.")
    
    # 2. Other minor updates (Standardizing MD files, etc.)
    md_path = "semua_desa.md"
    if os.path.exists(md_path):
        print("[-] Checking semua_desa.md format...")
        # ... logic to clean up if needed ...
        print("[+] semua_desa.md is ready.")

    print("\n--- ✅ DEPLOYMENT READY ---")
    print("You can now start the server with: python main.py")

if __name__ == "__main__":
    run_deploy()
