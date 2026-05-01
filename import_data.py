import pandas as pd
from models import SessionLocal, engine, Base, Achievement
import os

def import_excel():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    excel_file = "SPM Air Minum Cianjur.xlsx"
    if not os.path.exists(excel_file):
        print(f"File {excel_file} not found.")
        return

    print(f"Importing data from {excel_file}...")
    
    # Read Excel, skipping the first 5 rows
    df = pd.read_excel(excel_file, header=None, skiprows=5)
    df = df.fillna("")

    total_imported_sr = 0

    for index, row in df.iterrows():
        try:
            # Check if Kecamatan (row[1]) and Desa (row[2]) are both empty
            if (not str(row[1]).strip() or row[1] == "") and (not str(row[2]).strip() or row[2] == ""):
                continue
            
            def safe_int(val):
                if val == "" or str(val) == "-" or val is None:
                    return 0
                try:
                    # If it's already a number (float/int), just round it
                    if isinstance(val, (int, float)):
                        return int(round(val))
                    
                    # If it's a string, clean it
                    s = str(val).strip()
                    if not s: return 0
                    
                    # Remove thousand separators if they exist (common in ID: 1.000)
                    # But wait, we saw 95.4 in the data. 
                    # If there's a dot AND a comma, comma is decimal.
                    # If there's only a dot, and it's like 1.234, it's likely thousands.
                    # If it's 1.2, it's decimal.
                    # Let's use pandas to_numeric which is more robust
                    num = pd.to_numeric(s.replace(',', '.'), errors='coerce')
                    if pd.isna(num):
                        return 0
                    return int(round(num))
                except:
                    return 0

            sr = safe_int(row[21])
            kk = safe_int(row[22])
            jiwa = safe_int(row[23])
            target = safe_int(row[25])
            
            total_imported_sr += sr

            item = Achievement(
                no_urut=int(float(row[0])) if row[0] != "" else 0,
                kecamatan=str(row[1]).strip(),
                desa=str(row[2]).strip(),
                tahun=str(row[5]).strip(),
                sumber_dana=str(row[6]).strip(),
                program=str(row[7]).strip(),
                pokmas=str(row[8]).strip(),
                
                # Kelembagaan / Pengurus
                perdes=str(row[9]).strip(),
                kepala=str(row[10]).strip(),
                bendahara=str(row[11]).strip(),
                sekretaris=str(row[12]).strip(),
                
                # Data Teknis
                sumber_mata_air_kap=str(row[13]).strip(),
                sistem_layanan=str(row[14]).strip(),
                sumber_air_tanah_kap=str(row[15]).strip(),
                lain_lain_kap=str(row[16]).strip(),
                
                # Parameter
                tarif_dasar_hukum=str(row[17]).strip(),
                iuran_nominal=str(row[18]).strip(),
                pendapatan_rata2=str(row[19]).strip(),
                biaya_operasional=str(row[20]).strip(),
                
                # Numeric columns (Rounded)
                jumlah_sr=sr,
                jumlah_kk=kk,
                jumlah_jiwa=jiwa,
                target=target,
            )
            db.add(item)
        except Exception as e:
            print(f"Error importing row {index}: {e}")
            continue

    db.commit()
    print(f"Imported {db.query(Achievement).count()} records.")
    print(f"Total SR in DB: {total_imported_sr}")
    db.close()

if __name__ == "__main__":
    import_excel()
