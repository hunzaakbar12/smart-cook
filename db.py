import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "smart_cook_ultra_simple_BIG.db")

con = sqlite3.connect(db_path)
cur = con.cursor()


print("🔍 Tabellen in der Datenbank:")
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()

for t in tables:
    print(" -", t[0])

print("\n🔍 Spalten im 'recipes'-Tabelle:")
cur.execute("PRAGMA table_info(recipes);")
columns = cur.fetchall()

for col in columns:
    print(col)

con.close()
