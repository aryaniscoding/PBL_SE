import sqlite3

conn = sqlite3.connect("number_plates.db")
cursor = conn.cursor()

with open("dump.sql", "w") as f:
    for line in conn.iterdump():
        f.write(f"{line}\n")

conn.close()
print("Database dump saved to dump.sql")
