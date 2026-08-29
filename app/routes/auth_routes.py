from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, checjuishfeh
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
