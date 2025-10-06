import os
import re
import sqlite3
import pdfplumber
from db import get_connection


def add_balance_sheet_data_bulk(records):
   
    if not records:
        return
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_company_year
        ON balance_sheets(company_id, year)
    """)

    cur.executemany("""
        INSERT INTO balance_sheets (company_id, year, revenue, assets, liabilities, profit)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id, year)
        DO UPDATE SET revenue=excluded.revenue,
                      assets=excluded.assets,
                      liabilities=excluded.liabilities,
                      profit=excluded.profit
    """, records)

    conn.commit()
    conn.close()


def list_companies():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM companies")
    companies = cur.fetchall()
    conn.close()
    return companies


def choose_company(user):
    companies = list_companies()

 
    if user["role"].lower() != "groupadmin":
        companies = [c for c in companies if c[0] == user["company_id"]]

    print("\nSelect company by ID:")
    for cid, cname in companies:
        print(f"{cid}: {cname}")

    while True:
        try:
            company_id = int(input("Company ID: ").strip())
            if user["role"].lower() == "groupadmin" or company_id == user["company_id"]:
                return company_id
            else:
                print("Access Denied: You cannot upload data for this company.")
        except ValueError:
            print("Please enter a valid number.")


def clean_number(val):
  
    if not val:
        return None
    val = val.strip().replace(",", "")
    val = re.sub(r"[^\d().-]", "", val)
    if val.startswith("(") and val.endswith(")"):
        val = "-" + val[1:-1]
    try:
        return float(val)
    except ValueError:
        return None


def extract_tables(pdf_path):
   
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_tables()
                for table in extracted:
                    
                    if table and len(table) > 2 and len(table[0]) >= 5:
                        tables.append(table)
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return tables


def extract_and_store(pdf_path, user):
    print("Extracting tables from PDF...")
    tables = extract_tables(pdf_path)
    if not tables:
        print("No valid tables found in PDF.")
        return

    company_id = choose_company(user)
    inserted_records = []
    total_rows = 0

    for table in tables:
        headers = [h.strip().lower() for h in table[0] if h]
        col_map = {name: idx for idx, name in enumerate(headers)}

       
        required = ["year", "revenue", "assets", "liabilities", "profit"]
        if not all(any(r in h for h in headers) for r in required):
            continue  

        for i in range(1, len(table)):
            row = table[i]
            if len(row) < 5:
                continue
            try:
                year = int(re.sub(r"[^\d]", "", row[col_map.get("year", 0)]))
                revenue = clean_number(row[col_map.get("revenue", 1)])
                assets = clean_number(row[col_map.get("assets", 2)])
                liabilities = clean_number(row[col_map.get("liabilities", 3)])
                profit = clean_number(row[col_map.get("profit", 4)])
                if None in [year, revenue, assets, liabilities, profit]:
                    continue
                inserted_records.append(
                    (company_id, year, revenue, assets, liabilities, profit)
                )
                total_rows += 1
            except Exception as e:
                print(f"Skipping row {i}: {e}")

    if inserted_records:
        add_balance_sheet_data_bulk(inserted_records)
        print(f"{total_rows} rows of balance sheet data stored/updated successfully.")
    else:
        print("No valid balance sheet data found.")


def main_menu(user):
    while True:
        print("\n--- Balance Sheet PDF Menu ---")
        print("1. Add balance sheet data from PDF")
        print("2. Exit to main menu")
        choice = input("Enter choice (1/2): ").strip()

        if choice == "1":
            pdf_path = input("Enter full path to the PDF file: ").strip()
            if not os.path.isfile(pdf_path):
                print("Invalid file path. Try again.")
                continue
            extract_and_store(pdf_path, user)
        elif choice == "2":
            print("Returning to main menu.")
            break
        else:
            print("Invalid choice. Try again.")


extract_and_save=extract_and_store
