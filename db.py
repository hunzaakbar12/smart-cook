import sqlite3

con = sqlite3.connect("smart_cook_ultra_simple_BIG.db")
cur = con.cursor()
cur.execute("PRAGMA table_info(recipes);")

for column in cur.fetchall():
    print(column)

con.close()
