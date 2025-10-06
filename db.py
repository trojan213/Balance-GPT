
import sqlite3

DB_NAME = "balance_gpt.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

# get companies a user can access
def list_companies(user):
    conn = get_connection()
    cur = conn.cursor()

    if user["role"].lower() == "groupadmin":
        cur.execute("SELECT id, name FROM companies")
    else:
        # only the user's assigned company
        cur.execute("SELECT id, name FROM companies WHERE id=?", (user["company_id"],))

    companies = cur.fetchall()
    conn.close()
    return [{"id": cid, "name": name} for cid, name in companies]

# get balance sheets for a company, enforcing access
def get_balance_sheet(user, company_id=None):
    conn = get_connection()
    cur = conn.cursor()

    # Check permissions
    allowed_companies = [c['id'] for c in list_companies(user)]
    if company_id and company_id not in allowed_companies:
        conn.close()
        return []  # access denied, return empty

    if user["role"].lower() == "groupadmin" and company_id:
        cur.execute(
            "SELECT year, revenue, assets, liabilities, profit FROM balance_sheets "
            "WHERE company_id=? ORDER BY year ASC", (company_id,)
        )
    elif user["role"].lower() != "groupadmin":
        cur.execute(
            "SELECT year, revenue, assets, liabilities, profit FROM balance_sheets "
            "WHERE company_id=?", (user["company_id"],)
        )
    else:
        cur.execute(
            "SELECT companies.name, year, revenue, assets, liabilities, profit "
            "FROM balance_sheets JOIN companies ON balance_sheets.company_id = companies.id "
            "ORDER BY companies.name, year"
        )

    rows = cur.fetchall()
    conn.close()
    return rows


def create_tables():
    conn = get_connection()
    cur = conn.cursor()

   
    cur.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            parent_group TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('analyst','ceo','GroupAdmin')),
            company_id INTEGER,
            FOREIGN KEY(company_id) REFERENCES companies(id)
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS balance_sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            revenue REAL,
            assets REAL,
            liabilities REAL,
            profit REAL,
            FOREIGN KEY(company_id) REFERENCES companies(id)
        )
    """)

    conn.commit()
    conn.close()


def seed_data():
    conn = get_connection()
    cur = conn.cursor()


    companies = [
        ("Reliance Retail", "Reliance Group"),
        ("Jio Platforms", "Reliance Group"),
        ("Reliance Industries", "Reliance Group"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO companies (name, parent_group) VALUES (?,?)", companies
    )

    cur.execute("SELECT id, name FROM companies")
    company_map = {name: cid for cid, name in cur.fetchall()}

    users = [
        ("rajiv", "pass123", "analyst", company_map["Reliance Retail"]),
        ("sneha", "pass123", "analyst", company_map["Jio Platforms"]),
        ("amit", "pass123", "ceo", company_map["Reliance Retail"]),
        ("ramesh", "pass123", "ceo", company_map["Jio Platforms"]),
        ("ambani", "ambani123", "GroupAdmin", None),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO users (username,password,role,company_id) VALUES (?,?,?,?)",
        users
    )


    balances = [
        (company_map["Reliance Retail"], 2022, 220000, 500000, 200000, 30000),
        (company_map["Reliance Retail"], 2023, 260000, 520000, 210000, 35000),
        (company_map["Jio Platforms"], 2022, 180000, 400000, 150000, 25000),
        (company_map["Jio Platforms"], 2023, 202000, 420000, 160000, 28000),
        (company_map["Reliance Industries"], 2022, 450000, 1000000, 600000, 70000),
        (company_map["Reliance Industries"], 2023, 480000, 1050000, 620000, 75000),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO balance_sheets (company_id, year, revenue, assets, liabilities, profit) VALUES (?,?,?,?,?,?)",
        balances
    )

    conn.commit()
    conn.close()

def add_balance_sheet_data(company_name, year, revenue, assets, liabilities, profit):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM companies WHERE name=?", (company_name,))
    result = cur.fetchone()
    if not result:
        print(f"Company '{company_name}' not found in database.")
        conn.close()
        return

    company_id = result[0]

  
    cur.execute("""
        INSERT INTO balance_sheets (company_id, year, revenue, assets, liabilities, profit)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id, year)
        DO UPDATE SET revenue=excluded.revenue, assets=excluded.assets, 
                      liabilities=excluded.liabilities, profit=excluded.profit
    """, (company_id, year, revenue, assets, liabilities, profit))

    conn.commit()
    conn.close()
    print(f"✅ Balance sheet data added/updated for {company_name} ({year})")


if __name__ == "__main__":
    create_tables()
    seed_data()
    print("Database initialized and dummy data seeded.")
