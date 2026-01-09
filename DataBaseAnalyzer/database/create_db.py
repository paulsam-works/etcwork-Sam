import sqlite3
import pandas as pd

# create a connection to the SQLite database (or create it if it doesn't exist)
connection = sqlite3.connect('sales.db')
cursor = connection.cursor()

# Create a sample table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY,
        product TEXT,
        category TEXT,
        amount REAL,
        date TEXT
    )
''')

# Insert some data
data = [
    (1, 'Laptop', 'Electronics', 1200.00, '2025-01-10'),
    (2, 'Mouse', 'Electronics', 25.50, '2025-01-11'),
    (3, 'T-Shirt', 'Apparel', 20.00, '2025-01-12'),
    (4, 'Laptop', 'Electronics', 1350.00, '2025-02-01'),
    (5, 'Jeans', 'Apparel', 45.99, '2025-02-05'),
    (6, 'TV', 'Electronics', 800.00, '2025-03-01'),
    (7, 'Sneakers', 'Apparel', 60.00, '2025-03-05')
]
cursor.executemany("INSERT INTO sales (id, product, category, amount, date) VALUES (?, ?, ?, ?, ?)", data)
connection.commit()
connection.close()
print("Sample sales.db database created.")



