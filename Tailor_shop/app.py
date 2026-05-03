import os

import mysql.connector
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DATABASE_NAME = os.getenv("MYSQL_DATABASE", "tailor_shop")

if not DATABASE_NAME.replace("_", "").isalnum():
    raise ValueError("MYSQL_DATABASE can only contain letters, numbers, and underscores.")

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "user": os.getenv("MYSQL_USER", "tailor_app"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": DATABASE_NAME,
}


def get_db_connection(use_database=True):
    config = DB_CONFIG.copy()
    if not use_database:
        config.pop("database")
    return mysql.connector.connect(**config)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            neck DECIMAL(5, 2) NOT NULL,
            waist DECIMAL(5, 2) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute("SELECT COUNT(*) AS total FROM orders")
    if cursor.fetchone()["total"] == 0:
        cursor.executemany(
            "INSERT INTO orders (name, neck, waist, status) VALUES (%s, %s, %s, %s)",
            [
                ("Alex Rivera", 15.5, 32, "In Progress"),
                ("Sam Chen", 16, 34, "Pending"),
            ],
        )

    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    conn.close()
    return render_template('index.html', orders=orders)

@app.route('/add', methods=['GET', 'POST'])
def add_order():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO orders (name, neck, waist, status) VALUES (%s, %s, %s, %s)",
            (
                request.form['name'].strip(),
                float(request.form['neck']),
                float(request.form['waist']),
                "Pending",
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add_order.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

init_db()

if __name__ == '__main__':
    app.run(debug=True)
