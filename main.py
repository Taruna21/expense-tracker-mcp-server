import os
import sqlite3
import tempfile
from fastmcp import FastMCP

DB_PATH = os.path.join(tempfile.gettempdir(), "expenses.db")
mcp = FastMCP(
    name="Expense Tracker",
    instructions="A tool to track expenses and perform calculations.",
)


def ensure_table():
    """Create the expenses table if missing, and add the category column to older tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Uncategorized'
        )
        """
    )
    cursor.execute("PRAGMA table_info(expenses)")
    columns = [row[1] for row in cursor.fetchall()]
    if "category" not in columns:
        cursor.execute(
            "ALTER TABLE expenses ADD COLUMN category TEXT NOT NULL DEFAULT 'Uncategorized'"
        )
    conn.commit()
    conn.close()


# Runs once at startup (plain function call, no event loop needed)
ensure_table()


@mcp.tool
async def add_expense(description: str, amount: float, date: str, category: str = "Uncategorized"):
    """Add a new expense to the database."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (description, amount, date, category) VALUES (?, ?, ?, ?)",
        (description, amount, date, category),
    )
    conn.commit()
    conn.close()
    return f"Expense '{description}' of amount {amount} added on {date} (category: {category})."


@mcp.tool
async def get_expenses():
    """Retrieve all expenses from the database."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses")
    expenses = cursor.fetchall()
    conn.close()
    return expenses


@mcp.tool
async def calculate_total_expenses():
    """Calculate the total amount of expenses."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM expenses")
    total = cursor.fetchone()[0]
    conn.close()
    return total if total is not None else 0.0


@mcp.tool
async def calculate_average_expense():
    """Calculate the average expense amount."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(amount) FROM expenses")
    average = cursor.fetchone()[0]
    conn.close()
    return average if average is not None else 0.0


@mcp.tool
async def list_expenses_by_date(date: str):
    """List all expenses for a specific date."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE date = ?", (date,))
    expenses = cursor.fetchall()
    conn.close()
    return expenses


@mcp.tool
async def delete_expense(expense_id: int):
    """Delete an expense by its ID."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()
    return f"Expense with ID {expense_id} has been deleted."


@mcp.tool
async def update_expense(
    expense_id: int,
    description: str = None,
    amount: float = None,
    date: str = None,
    category: str = None,
):
    """Update an existing expense."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    updates = []
    params = []

    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)
    if date is not None:
        updates.append("date = ?")
        params.append(date)
    if category is not None:
        updates.append("category = ?")
        params.append(category)

    if updates:
        update_query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
        params.append(expense_id)
        cursor.execute(update_query, tuple(params))
        conn.commit()

    conn.close()
    return f"Expense with ID {expense_id} has been updated."


@mcp.tool
async def get_expense_by_id(expense_id: int):
    """Retrieve a specific expense by its ID."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    expense = cursor.fetchone()
    conn.close()
    return expense


@mcp.tool
async def get_expenses_by_description(description: str):
    """Retrieve expenses that match a specific description."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE description LIKE ?", (f"%{description}%",))
    expenses = cursor.fetchall()
    conn.close()
    return expenses


@mcp.tool
async def get_expenses_by_amount_range(min_amount: float, max_amount: float):
    """Retrieve expenses within a specific amount range."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE amount BETWEEN ? AND ?", (min_amount, max_amount))
    expenses = cursor.fetchall()
    conn.close()
    return expenses


@mcp.tool
async def get_expenses_by_date_range(start_date: str, end_date: str):
    """Retrieve expenses within a specific date range."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE date BETWEEN ? AND ?", (start_date, end_date))
    expenses = cursor.fetchall()
    conn.close()
    return expenses


@mcp.tool
async def get_expense_statistics():
    """Retrieve statistics about the expenses."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(amount), AVG(amount), MIN(amount), MAX(amount) FROM expenses")
    stats = cursor.fetchone()
    conn.close()

    return {
        "total_expenses": stats[0],
        "total_amount": stats[1] if stats[1] is not None else 0.0,
        "average_amount": stats[2] if stats[2] is not None else 0.0,
        "min_amount": stats[3] if stats[3] is not None else 0.0,
        "max_amount": stats[4] if stats[4] is not None else 0.0,
    }


@mcp.tool
async def clear_all_expenses():
    """Delete all expenses from the database."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses")
    conn.commit()
    conn.close()
    return "All expenses have been cleared."


@mcp.tool
async def export_expenses_to_csv(file_path: str):
    """Export all expenses to a CSV file."""
    import csv

    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, description, amount, date, category FROM expenses")
    expenses = cursor.fetchall()
    conn.close()

    with open(file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["ID", "Description", "Amount", "Date", "Category"])
        writer.writerows(expenses)

    return f"Expenses have been exported to {file_path}."


@mcp.tool
async def import_expenses_from_csv(file_path: str):
    """Import expenses from a CSV file."""
    import csv

    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(file_path, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            cursor.execute(
                "INSERT INTO expenses (description, amount, date, category) VALUES (?, ?, ?, ?)",
                (
                    row["Description"],
                    float(row["Amount"]),
                    row["Date"],
                    row.get("Category") or "Uncategorized",
                ),
            )

    conn.commit()
    conn.close()

    return f"Expenses have been imported from {file_path}."


@mcp.tool
async def get_expenses_summary_by_month():
    """Retrieve a summary of expenses grouped by month."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT strftime('%Y-%m', date) AS month, SUM(amount) AS total_amount
        FROM expenses
        GROUP BY month
        ORDER BY month
        """
    )
    summary = cursor.fetchall()
    conn.close()
    return summary


@mcp.tool
async def get_expenses_summary_by_category():
    """Retrieve a summary of expenses grouped by category."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT category, SUM(amount) AS total_amount
        FROM expenses
        GROUP BY category
        ORDER BY total_amount DESC
        """
    )
    summary = cursor.fetchall()
    conn.close()
    return summary


@mcp.tool
async def get_expenses_summary_by_year():
    """Retrieve a summary of expenses grouped by year."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT strftime('%Y', date) AS year, SUM(amount) AS total_amount
        FROM expenses
        GROUP BY year
        ORDER BY year
        """
    )
    summary = cursor.fetchall()
    conn.close()
    return summary


@mcp.tool
async def get_expenses_summary_by_week():
    """Retrieve a summary of expenses grouped by week."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT strftime('%Y-%W', date) AS week, SUM(amount) AS total_amount
        FROM expenses
        GROUP BY week
        ORDER BY week
        """
    )
    summary = cursor.fetchall()
    conn.close()
    return summary


@mcp.tool
async def get_expenses_summary_by_day():
    """Retrieve a summary of expenses grouped by day."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT date, SUM(amount) AS total_amount
        FROM expenses
        GROUP BY date
        ORDER BY date
        """
    )
    summary = cursor.fetchall()
    conn.close()
    return summary


@mcp.tool
async def get_expenses_summary_by_description():
    """Retrieve a summary of expenses grouped by description."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT description, SUM(amount) AS total_amount
        FROM expenses
        GROUP BY description
        ORDER BY total_amount DESC
        """
    )
    summary = cursor.fetchall()
    conn.close()
    return summary


@mcp.tool
async def get_expenses_summary_by_amount_range(min_amount: float, max_amount: float):
    """Retrieve a summary of expenses grouped by amount range."""
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            CASE
                WHEN amount < ? THEN 'Below Min'
                WHEN amount > ? THEN 'Above Max'
                ELSE 'Within Range'
            END AS amount_range,
            SUM(amount) AS total_amount
        FROM expenses
        GROUP BY amount_range
        """,
        (min_amount, max_amount),
    )
    summary = cursor.fetchall()
    conn.close()
    return summary


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)