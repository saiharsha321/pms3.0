import sqlite3
import os
import pandas as pd
from pms.models import User, Department, Permission, Club, Event

# Path to database relative to where script is run
DB_PATH = os.path.join('pms', 'instance', 'pms.db')

def inspect_table(table_name, conn):
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        if df.empty:
            print(f"\nTable '{table_name}' is empty.")
        else:
            print(f"\n--- Data in '{table_name}' ---")
            print(df.to_string(index=False))
            print(f"\nTotal rows: {len(df)}")
    except Exception as e:
        print(f"Error reading table {table_name}: {e}")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at: {DB_PATH}")
        print("Make sure you are running this script from the project root (d:/pms 3.0)")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Connected to database: {DB_PATH}")
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]

    while True:
        print("\nAvailable Tables:")
        for i, t in enumerate(tables):
            print(f"{i+1}. {t}")
        
        choice = input("\nEnter table number to view (or 'q' to quit): ").strip()
        
        if choice.lower() == 'q':
            break
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tables):
                inspect_table(tables[idx], conn)
            else:
                print("Invalid number.")
        except ValueError:
            print("Invalid input.")

    conn.close()
    print("Closed connection.")

if __name__ == "__main__":
    main()
