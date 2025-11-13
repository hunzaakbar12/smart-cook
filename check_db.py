import sqlite3

conn = sqlite3.connect("db.sqlite")
cursor = conn.cursor()

# Alle Tabellen anzeigen
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("📂 Tabellen in der Datenbank:")
for t in tables:
    print(" -", t[0])

# Wenn Tabellen existieren, versuch die erste anzuzeigen
if tables:
    table_name = tables[0][0]
    print(f"\n📄 Erste 5 Zeilen aus '{table_name}':")
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
else:
    print("\n⚠️  Keine Tabellen gefunden – die Datenbank ist leer oder wurde noch nicht befüllt.")

conn.close()

