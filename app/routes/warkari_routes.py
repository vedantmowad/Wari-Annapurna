from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from app.models.db import mysql

warkari_bp = Blueprint('warkari', __name__, url_prefix='/warkari')

@warkari_bp.route('/dashboard')
def dashboard():

    if 'user_id' not in session or session.get('role') != 'warkari':
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM annadan_centres
        WHERE status = 'active'
    """)

    available_centres = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COALESCE(SUM(ms.available_meals), 0)
        FROM meal_services ms
        JOIN annadan_centres ac
            ON ac.id = ms.centre_id
        WHERE ac.status = 'active'
        AND ms.status = 'available'
        AND ms.service_date = CURDATE()
    """)

    available_meals = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COUNT(*)
        FROM meal_services ms
        JOIN annadan_centres ac
            ON ac.id = ms.centre_id
        WHERE ac.status = 'active'
        AND ms.status = 'available'
        AND ms.service_date = CURDATE()
    """)

    active_services = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COUNT(*)
        FROM annadan_centres
        WHERE status = 'active'
    """)

    nearby_centres = cur.fetchone()[0] or 0

    cur.close()

    return render_template(
        'warkari/dashboard.html',
        available_centres=available_centres,
        available_meals=available_meals,
        active_services=active_services,
        nearby_centres=nearby_centres
    )
