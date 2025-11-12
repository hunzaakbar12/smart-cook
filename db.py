import sqlite3

conn = sqlite3.connect("smart_cook_ultra_simple_BIG.db")
cur = conn.cursor()
cur.execute("SELECT name FROM recipes LIMIT 10;")
print(cur.fetchall())
conn.close()