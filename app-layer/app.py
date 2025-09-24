from flask import Flask, render_template, request, redirect, flash
import mysql.connector
from mysql.connector import Error
import os
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'mysql-db'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'Ujwal9494'),
    'database': os.getenv('DB_NAME', 'database-1'),
    'autocommit': True
}

def wait_for_db(max_retries=30, retry_delay=5):
    """Wait for database to be ready"""
    for attempt in range(max_retries):
        try:
            connection = mysql.connector.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                port=3306
            )
            connection.close()
            logger.info("✅ Database is ready!")
            return True
        except Error as e:
            logger.info(f"⏳ Database not ready yet (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("❌ Max retries reached. Could not connect to database.")
                return False

def get_db_connection():
    """Get database connection"""
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise e

def init_database():
    """Initialize database and create tables"""
    try:
        # Wait for database to be ready first
        if not wait_for_db():
            raise Exception("Database not available")
        
        # Connect without specifying database first
        connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            port=3306
        )
        cursor = connection.cursor()
        
        # Create database if not exists - USE BACKTICKS for database name with hyphens
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_config['database']}`")
        logger.info(f"✅ Database '{db_config['database']}' is ready!")
        
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
        logger.info("✅ Table 'contact_queries' is ready!")
        
        cursor.close()
        db.close()
        
    except Error as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise e

# Initialize database on startup with error handling
def initialize_app():
    """Initialize the application with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            init_database()
            logger.info("✅ Application initialized successfully!")
            return
        except Exception as e:
            logger.error(f"❌ Initialization attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in 10 seconds...")
                time.sleep(10)
            else:
                logger.error("❌ Max initialization retries reached. Application may not function properly.")

# Start initialization when app starts
initialize_app()

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
        cursor.execute("SELECT name, email, phone, message, created_at FROM contact_queries ORDER BY id DESC")
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
    app.run(host='0.0.0.0', port=5000, debug=False)
