import sqlite3
import re

def update_targets():
    conn = sqlite3.connect('spm_am.db')
    cursor = conn.cursor()
    
    with open('semua_desa.md', 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Split by tabs or multiple spaces
            parts = re.split(r'\t|\s{2,}', line)
            if len(parts) >= 3:
                kec = parts[0].strip().upper()
                desa = parts[1].strip().upper()
                target_raw = parts[2].strip()
                
                # Handle Indonesian formatting: 2.375 -> 2375
                # Remove dots (thousands) and replace comma with dot (decimals)
                target_clean = target_raw.replace('.', '')
                try:
                    target_val = int(round(float(target_clean)))
                    
                    print(f"Updating {kec} - {desa} with Target: {target_val}")
                    cursor.execute("""
                        UPDATE achievements 
                        SET target = ? 
                        WHERE UPPER(kecamatan) = ? AND UPPER(desa) = ?
                    """, (target_val, kec, desa))
                except Exception as e:
                    print(f"Error parsing target '{target_raw}' for {desa}: {e}")
            
    conn.commit()
    conn.close()
    print("Target updates complete.")

if __name__ == "__main__":
    update_targets()
