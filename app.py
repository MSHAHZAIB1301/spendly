from flask import Flask, render_template, request, redirect, url_for, session, flash
import hashlib
import secrets
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import traceback

# Import database functions
from database.db import get_db, init_db, is_postgres_available

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Session configuration - signed cookies (stored in browser, not server)
app.config['SESSION_TYPE'] = 'cookie'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7 days
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Only set SECURE=True if using HTTPS
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('HTTPS', 'false').lower() == 'true'

# ------------------------------------------------------------------ #
# Email Configuration                                                  #
# ------------------------------------------------------------------ #

SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'mhamza4073@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'xmsu jemc qtmk zptd')
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# ------------------------------------------------------------------ #
# Auth helpers                                                         #
# ------------------------------------------------------------------ #

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_by_email(email):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return dict(user)
        return None
    except Exception as e:
        print(f"Error in get_user_by_email: {e}")
        traceback.print_exc()
        return None

def get_user_by_id(user_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return dict(user)
        return None
    except Exception as e:
        print(f"Error in get_user_by_id: {e}")
        traceback.print_exc()
        return None

def create_user(name, email, password):
    try:
        conn = get_db()
        cursor = conn.cursor()

        if is_postgres_available():
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (name, email, hash_password(password))
            )
            result = cursor.fetchone()
            user_id = result['id'] if result else None
        else:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, hash_password(password))
            )
            user_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return user_id
    except Exception as e:
        print(f"Error in create_user: {e}")
        traceback.print_exc()
        if conn:
            conn.close()
        return None

def verify_login(email, password):
    try:
        user = get_user_by_email(email)
        if user and user['password_hash'] == hash_password(password):
            return user
        return None
    except Exception as e:
        print(f"Error in verify_login: {e}")
        traceback.print_exc()
        return None

def update_user_password(email, new_password):
    """Update password for a user by email"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE email = %s",
            (hash_password(new_password), email)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error in update_user_password: {e}")
        traceback.print_exc()
        return False

# ------------------------------------------------------------------ #
# Routes                                                               #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template("landing.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required")

        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters")

        user_id = create_user(name, email, password)
        if user_id is None:
            return render_template("register.html", error="Email already registered or database error")

        session['user_id'] = user_id
        session['user_name'] = name
        flash("Account created successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = verify_login(email, password)
        if user is None:
            return render_template("login.html", error="Invalid email or password")

        session['user_id'] = user['id']
        session['user_name'] = user['name']
        flash("Welcome back!", "success")
        return redirect(url_for('dashboard'))

    return render_template("login.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            return render_template("forgot_password.html", error="Email is required")

        user = get_user_by_email(email)
        if user:
            # Generate reset token and create link directly
            reset_token = secrets.token_urlsafe(32)
            reset_link = url_for('reset_password', token=reset_token, _external=True)

            # Show link directly on page (since email is not working)
            return render_template("forgot_password.html",
                success="Use the link below to reset your password:",
                reset_link=reset_link,
                user_email=email)
        else:
            # Don't reveal if email exists or not for security
            return render_template("forgot_password.html", success="If that email exists, a reset link has been sent.")

    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    # For demo, we'll store email in a simple dict (use Redis/DB in production)
    # For now, just allow any token to work with email from form
    global reset_tokens
    try:
        reset_tokens
    except NameError:
        reset_tokens = {}

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not password or not confirm_password:
            return render_template("reset_password.html", error="All fields are required", token=token)

        if len(password) < 8:
            return render_template("reset_password.html", error="Password must be at least 8 characters", token=token)

        if password != confirm_password:
            return render_template("reset_password.html", error="Passwords do not match", token=token)

        # Update password in database
        if update_user_password(email, password):
            flash("Password updated successfully! You can now login.", "success")
            return redirect(url_for('login'))
        else:
            return render_template("reset_password.html", error="Invalid email or token", token=token)

    return render_template("reset_password.html", token=token)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out", "info")
    return redirect(url_for('landing'))

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = get_user_by_id(session['user_id'])
    if user is None:
        session.clear()
        return redirect(url_for('login'))

    # Check for search query (day, month, year)
    search_day = request.args.get('search_day', '')
    search_month = request.args.get('search_month', '')
    search_year = request.args.get('search_year', '')

    conn = get_db()
    cursor = conn.cursor()

    # Build date filter based on search or default to current month
    if search_day and search_month and search_year:
        # Full date search - format as YYYY-MM-DD
        search_date = f"{search_year}-{search_month.zfill(2)}-{search_day.zfill(2)}"
        if is_postgres_available():
            date_filter = "date::timestamp = %s::timestamp"
        else:
            date_filter = "date = %s"
        date_param = search_date
    elif search_month and search_year:
        # Month + Year search
        search_month_formatted = f"{search_year}-{search_month.zfill(2)}"
        if is_postgres_available():
            date_filter = "TO_CHAR(date::timestamp, 'YYYY-MM') = %s"
        else:
            date_filter = "strftime('%Y-%m', date) = %s"
        date_param = search_month_formatted
    elif search_year:
        # Year only search
        if is_postgres_available():
            date_filter = "TO_CHAR(date::timestamp, 'YYYY') = %s"
        else:
            date_filter = "strftime('%Y', date) = %s"
        date_param = search_year
    else:
        # Default - current month
        if is_postgres_available():
            date_filter = "TO_CHAR(date::timestamp, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM')"
        else:
            date_filter = "strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
        date_param = None

    # Get expenses
    if date_param:
        cursor.execute(f"""
            SELECT * FROM expenses
            WHERE user_id = %s AND {date_filter}
            ORDER BY date DESC
        """, (session['user_id'], date_param))
    else:
        cursor.execute(f"""
            SELECT * FROM expenses
            WHERE user_id = %s AND {date_filter}
            ORDER BY date DESC
        """, (session['user_id'],))

    expenses = [dict(row) for row in cursor.fetchall()]

    # Get category totals
    if date_param:
        cursor.execute(f"""
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = %s AND {date_filter}
            GROUP BY category
        """, (session['user_id'], date_param))
    else:
        cursor.execute(f"""
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = %s AND {date_filter}
            GROUP BY category
        """, (session['user_id'],))

    categories = [dict(row) for row in cursor.fetchall()]

    # Total
    if date_param:
        cursor.execute(f"""
            SELECT SUM(amount) as total
            FROM expenses
            WHERE user_id = %s AND {date_filter}
        """, (session['user_id'], date_param))
    else:
        cursor.execute(f"""
            SELECT SUM(amount) as total
            FROM expenses
            WHERE user_id = %s AND {date_filter}
        """, (session['user_id'],))

    total = cursor.fetchone()['total'] or 0

    conn.close()

    return render_template("dashboard.html",
                         user_name=session['user_name'],
                         expenses=expenses,
                         categories=categories,
                         total=total,
                         search_day=search_day,
                         search_month=search_month,
                         search_year=search_year)

@app.route("/profile")
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = get_user_by_id(session['user_id'])
    if user is None:
        session.clear()
        return redirect(url_for('login'))

    return render_template("profile.html", user=user)

# ------------------------------------------------------------------ #
# Expense routes                                                       #
# ------------------------------------------------------------------ #

@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")
        description = request.form.get("description", "")
        date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))

        if not amount or not category:
            return render_template("add_expense.html", error="Amount and category are required")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (user_id, amount, category, description, date) VALUES (%s, %s, %s, %s, %s)",
            (session['user_id'], float(amount), category, description, date)
        )
        conn.commit()
        conn.close()

        # Send email notification
        user = get_user_by_id(session['user_id'])
        if user:
            email_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #667eea;">New Expense Added! 💸</h2>
                <p>Hi {session['user_name']},</p>
                <p>Your expense has been recorded:</p>
                <table style="border-collapse: collapse; margin: 20px 0;">
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Amount:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">Rs.{float(amount):.2f}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Category:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{category}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Description:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{description or '-'}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Date:</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{date}</td></tr>
                </table>
                <p>Keep tracking your expenses with <strong>Spendly</strong>!</p>
            </body>
            </html>
            """
            send_email(user['email'], "New Expense Added - Spendly", email_body)

        flash("Expense added! Notification sent.", "success")
        return redirect(url_for('dashboard'))

    return render_template("add_expense.html")

@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE id = %s AND user_id = %s", (id, session['user_id']))
    expense = cursor.fetchone()
    conn.close()

    if not expense:
        flash("Expense not found", "error")
        return redirect(url_for('dashboard'))

    expense = dict(expense)

    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")
        description = request.form.get("description", "")
        date = request.form.get("date")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE expenses SET amount = %s, category = %s, description = %s, date = %s WHERE id = %s",
            (float(amount), category, description, date, id)
        )
        conn.commit()
        conn.close()

        flash("Expense updated!", "success")
        return redirect(url_for('dashboard'))

    return render_template("edit_expense.html", expense=expense)

@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = %s AND user_id = %s", (id, session['user_id']))
    conn.commit()
    conn.close()

    flash("Expense deleted", "info")
    return redirect(url_for('dashboard'))

# ------------------------------------------------------------------ #
# Init                                                                 #
# ------------------------------------------------------------------ #

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
