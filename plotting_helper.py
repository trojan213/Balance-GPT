import matplotlib.pyplot as plt
from db import get_connection

def fetch_balance_sheet_data(company_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT year, revenue, assets, liabilities, profit
        FROM balance_sheets
        JOIN companies ON balance_sheets.company_id = companies.id
        WHERE companies.name = ?
        ORDER BY year ASC
        """,
        (company_name,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def plot_balance_sheet(company_name):
    rows = fetch_balance_sheet_data(company_name)
    if not rows:
        print(f"No balance sheet data found for {company_name}.")
        return

    years = [r[0] for r in rows]
    revenue = [r[1] for r in rows]
    assets = [r[2] for r in rows]
    liabilities = [r[3] for r in rows]
    profit = [r[4] for r in rows]

    growth = [0] + [((revenue[i] - revenue[i-1])/revenue[i-1])*100 for i in range(1, len(revenue))]


    plt.figure(figsize=(10, 6))

    plt.subplot(2, 2, 1)
    plt.plot(years, revenue, marker='o', color='blue')
    plt.title(f"{company_name} Revenue")
    plt.xlabel("Year")
    plt.ylabel("Revenue")

    plt.subplot(2, 2, 2)
    plt.plot(years, profit, marker='o', color='green')
    plt.title(f"{company_name} Profit")
    plt.xlabel("Year")
    plt.ylabel("Profit")

    plt.subplot(2, 2, 3)
    plt.bar(years, assets, label='Assets', alpha=0.7)
    plt.bar(years, liabilities, label='Liabilities', alpha=0.7)
    plt.title(f"{company_name} Assets vs Liabilities")
    plt.xlabel("Year")
    plt.ylabel("Value")
    plt.legend()

    plt.subplot(2, 2, 4)
    plt.plot(years, growth, marker='o', color='purple')
    plt.title(f"{company_name} Revenue Growth %")
    plt.xlabel("Year")
    plt.ylabel("Growth %")

    plt.tight_layout()
    plt.show()
