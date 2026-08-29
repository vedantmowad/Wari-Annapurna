from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.db import mysql

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def landing():
    return render_template('landing.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)
        cur = mysql.connection.cursor()

        try:
            cur.execute("""
                INSERT INTO users
                (full_name, email, password, role)
                VALUES (%s, %s, %s, %s)
            """, (full_name, email, hashed_password, role))

            mysql.connection.commit()
            flash("Account created successfully. Please login.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            mysql.connection.rollback()
            flash(str(e), "danger")

        finally:
            cur.close()

    return render_template('auth/register.html')


@auth_bp.route('/register-centre', methods=['GET', 'POST'])
def register_centre():
    if request.method == 'POST':
        centre_name = request.form['centre_name']
        address = request.form['address']
        city = request.form['city']
        latitude = request.form['latitude']
        longitude = request.form['longitude']
        contact_phone = request.form['contact_phone']

        cur = mysql.connection.cursor()

        try:
            cur.execute("""
                INSERT INTO annadan_centres
                (centre_name, address, city, latitude, longitude,
                 contact_phone)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                centre_name, address, city, latitude,
                longitude, contact_phone
            ))

            mysql.connection.commit()
            flash("Annadan centre registered successfully! Please login.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            mysql.connection.rollback()
            flash(str(e), "danger")

        finally:
            cur.close()

    return render_template('auth/register_centre.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()

        try:
            cur.execute("""
                SELECT id, full_name, password, role
                FROM users
                WHERE email = %s
            """, (email,))

            user = cur.fetchone()

            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['role'] = user[3]

                if user[3] == "donor":
                    return redirect("/donor/dashboard")
                elif user[3] == "volunteer":
                    return redirect("/volunteer/dashboard")
                elif user[3] == "warkari":
                    return redirect("/warkari/dashboard")
                elif user[3] == "admin":
                    return redirect("/admin/dashboard")

                flash("Invalid user role.", "danger")
                return redirect(url_for('auth.landing'))

        except Exception as e:
            flash(f"Login error: {str(e)}", "danger")

        finally:
            cur.close()

    return render_template('auth/login.html')