import sqlite3
import os

DB_PATH = "./data/spm_am.db"

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- STARTING DATABASE MIGRATION ---")

    # 1. Add is_simspam column if missing
    try:
        cursor.execute("ALTER TABLE achievements ADD COLUMN is_simspam INTEGER DEFAULT 0")
        print("[+] Added is_simspam column.")
    except sqlite3.OperationalError:
        print("[!] is_simspam column already exists.")

    # 2. Standardize Names (Uppercase & No Spaces for Desa)
    print("[-] Standardizing village and kecamatan names...")
    cursor.execute("UPDATE achievements SET desa = UPPER(REPLACE(desa, ' ', ''))")
    cursor.execute("UPDATE achievements SET kecamatan = UPPER(kecamatan)")
    
    # 3. Ensure audit timestamps exist (Handled by models.py usually, but good to check)
    # SQLite doesn't support ADD COLUMN with DEFAULT current_timestamp easily for existing rows
    # without a full table recreation if we want it to be perfect, but for now we trust models.py
    
    conn.commit()
    print(f"[+] Data standardization complete. Affected rows: {cursor.rowcount}")
    conn.close()

    # 4. Clean semua_desa.md if exists
    md_path = "semua_desa.md"
    if os.path.exists(md_path):
        print("[-] Standardizing semua_desa.md...")
        new_lines = []
        with open(md_path, "r") as f:
            for line in f:
                parts = line.split('\t')
                if len(parts) >= 2:
                    parts[0] = parts[0].strip().upper() # Kecamatan
                    parts[1] = parts[1].strip().upper().replace(' ', '') # Desa
                new_lines.append('\t'.join(parts))
        
        with open(md_path, "w") as f:
            f.writelines(new_lines)
        print("[+] semua_desa.md cleaning complete.")

    print("--- MIGRATION FINISHED SUCCESSFULLY ---")

if __name__ == "__main__":
    run_migration()
