from flask import Flask, render_template, request, redirect, flash
import mysql.connector
from mysql.connector import Error
import os
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Database configuration - use environment variables or defaults
rds_host = os.getenv('DB_HOST', 'mysql')  # Use 'mysql' service name in Docker
rds_user = os.getenv('DB_USER', 'admin')
rds_password = os.getenv('DB_PASSWORD', 'Ujwal9494')
database = os.getenv('DB_NAME', 'database-1')

def get_db_connection():
    """Get database connection with retry logic"""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            connection = mysql.connector.connect(
                host=rds_host,
                user=rds_user,
                password=rds_password,
                database=database,
                autocommit=True
            )
            return connection
        except Error as e:
            print(f"❌ Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("❌ Max retries reached. Could not connect to database.")
                raise e

def init_database():
    """Initialize database and create tables"""
    try:
        # Connect without specifying database first
        connection = mysql.connector.connect(
            host=rds_host,
            user=rds_user,
            password=rds_password
        )
        cursor = connection.cursor()
        
        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        print(f"✅ Database '{database}' is ready!")
        
        # Close initial connection
        cursor.close()
        connection.close()
        
        # Connect to the specific database
        db = get_db_connection()
        cursor = db.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_queries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Table 'contact_queries' is ready!")
        
        cursor.close()
        db.close()
        
    except Error as e:
        print("❌ Database initialization failed:", e)
        raise e

# Initialize database on startup
try:
    init_database()
except Exception as e:
    print(f"Failed to initialize database: {e}")

# Flask routes
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/submit', methods=['POST'])
def submit():
    db = None
    cursor = None
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        if not name or not email or not message:
            flash('Please fill in all required fields.', 'error')
            return redirect("/")

        db = get_db_connection()
        cursor = db.cursor()
        
        sql = "INSERT INTO contact_queries (name, email, phone, message) VALUES (%s, %s, %s, %s)"
        values = (name, email, phone, message)

        cursor.execute(sql, values)
        db.commit()

        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect("/")
        
    except Exception as e:
        flash(f'Error submitting form: {str(e)}', 'error')
        return redirect("/")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@app.route('/admin')
def admin():
    db = None
    cursor = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT name, email, phone, message FROM contact_queries ORDER BY id DESC")
        results = cursor.fetchall()
        return render_template("admin.html", queries=results)
    except Exception as e:
        flash(f'Error loading admin data: {str(e)}', 'error')
        return redirect("/")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)