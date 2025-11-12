import sqlite3
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "smart_cook_ultra_simple_BIG.db")

 
connection = sqlite3.connect(db_path)
cursor = connection.cursor()


cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Tables names: ")
for t in tables:
    print("-", t[0])

connection.close()
