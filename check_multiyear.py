import sqlite3
conn = sqlite3.connect('spm_am.db')
cursor = conn.cursor()
cursor.execute("SELECT id, kecamatan, desa, tahun, jumlah_sr FROM achievements WHERE tahun LIKE '%/%'")
rows = cursor.fetchall()
for row in rows:
    print(row)
conn.close()
