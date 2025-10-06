from db import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("ALTER TABLE users RENAME TO users_old;")


cur.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('analyst','ceo','family','GroupAdmin')),
    company_id INTEGER,
    FOREIGN KEY(company_id) REFERENCES companies(id)
)
""")


cur.execute("""
INSERT INTO users (id, username, password, role, company_id)
SELECT id, username, password,
       CASE WHEN role='family' THEN 'GroupAdmin' ELSE role END,
       company_id
FROM users_old;
""")


cur.execute("DROP TABLE users_old;")

conn.commit()
conn.close()

print("Updated users table to allow GroupAdmin role!")
