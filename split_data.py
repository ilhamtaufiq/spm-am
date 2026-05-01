import sqlite3
import re

def split_years():
    conn = sqlite3.connect('spm_am.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM achievements WHERE tahun LIKE '%/%'")
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} records to split.")
    
    for row in rows:
        raw_years = re.split(r'[/]', row['tahun'])
        years = sorted(list(set([y.strip() for y in raw_years if y.strip()])))
        
        if not years:
            continue
            
        num_years = len(years)
        
        # Distribute values without losing decimals (using remainder)
        total_sr = row['jumlah_sr'] or 0
        total_kk = row['jumlah_kk'] or 0
        total_jiwa = row['jumlah_jiwa'] or 0
        total_target = row['target'] or 0
        
        base_sr = total_sr // num_years
        rem_sr = total_sr % num_years
        
        base_kk = total_kk // num_years
        rem_kk = total_kk % num_years
        
        base_jiwa = total_jiwa // num_years
        rem_jiwa = total_jiwa % num_years
        
        base_target = total_target // num_years
        rem_target = total_target % num_years
        
        for i, year in enumerate(years):
            # Add 1 to the first 'remainder' years to keep total consistent
            curr_sr = base_sr + (1 if i < rem_sr else 0)
            curr_kk = base_kk + (1 if i < rem_kk else 0)
            curr_jiwa = base_jiwa + (1 if i < rem_jiwa else 0)
            curr_target = base_target + (1 if i < rem_target else 0)
            
            cursor.execute("""
                INSERT INTO achievements (
                    no_urut, kecamatan, desa, tahun, sumber_dana, program, pokmas,
                    perdes, kepala, bendahara, sekretaris,
                    sumber_mata_air_kap, sistem_layanan, sumber_air_tanah_kap, lain_lain_kap,
                    tarif_dasar_hukum, iuran_nominal, pendapatan_rata2, biaya_operasional,
                    jumlah_sr, jumlah_kk, jumlah_jiwa, target
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['no_urut'], row['kecamatan'], row['desa'], year, 
                row['sumber_dana'], row['program'], row['pokmas'],
                row['perdes'], row['kepala'], row['bendahara'], row['sekretaris'],
                row['sumber_mata_air_kap'], row['sistem_layanan'], row['sumber_air_tanah_kap'], row['lain_lain_kap'],
                row['tarif_dasar_hukum'], row['iuran_nominal'], row['pendapatan_rata2'], row['biaya_operasional'],
                curr_sr, curr_kk, curr_jiwa, curr_target
            ))
        
        cursor.execute("DELETE FROM achievements WHERE id = ?", (row['id'],))
        
    conn.commit()
    print("Split complete with sum preservation.")
    conn.close()

if __name__ == "__main__":
    split_years()
