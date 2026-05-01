import sqlite3
import re

def get_db_villages():
    conn = sqlite3.connect('spm_am.db')
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT kecamatan, desa FROM achievements')
    rows = cursor.fetchall()
    conn.close()
    return set((r[0].strip().upper(), r[1].strip().upper()) for r in rows)

def get_md_villages():
    villages = set()
    with open('semua_desa.md', 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Handle space/tab separated
            parts = re.split(r'\t|\s{2,}', line)
            if len(parts) >= 2:
                kec = parts[0].strip().upper()
                desa = parts[1].strip().upper()
                villages.add((kec, desa))
    return villages

def sync():
    db_villages = get_db_villages()
    md_villages = get_md_villages()
    
    missing = md_villages - db_villages
    print(f"Total villages in MD: {len(md_villages)}")
    print(f"Total villages in DB: {len(db_villages)}")
    print(f"Missing villages: {len(missing)}")
    
    if missing:
        conn = sqlite3.connect('spm_am.db')
        cursor = conn.cursor()
        
        # We'll insert for 2024 and 2025
        years = ['2024', '2025']
        
        for kec, desa in sorted(list(missing)):
            print(f"Adding: {kec} - {desa}")
            for year in years:
                cursor.execute("""
                    INSERT INTO achievements (kecamatan, desa, tahun, jumlah_sr, jumlah_kk, jumlah_jiwa, target)
                    VALUES (?, ?, ?, 0, 0, 0, 0)
                """, (kec, desa, year))
        
        conn.commit()
        conn.close()
        print("Sync complete.")
    else:
        print("Everything is up to date.")

if __name__ == "__main__":
    sync()
