from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from app.models.db import mysql

warkari_bp = Blueprint('warkari', __name__, url_prefix='/warkari')


def calculate_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None

    radius = 6371

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(radius * c, 2)


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

@warkari_bp.route('/annadan')
def annadan():

    if 'user_id' not in session or session.get('role') != 'warkari':
        return redirect(url_for('auth.login'))

    city = request.args.get('city', '').strip()
    meal_type = request.args.get('meal_type', '').strip()
    sort_by = request.args.get('sort_by', 'availability').strip()

    cur = mysql.connection.cursor()

    query = """
        SELECT
            ac.id,
            ac.centre_name,
            ac.address,
            ac.city,
            ac.latitude,
            ac.longitude,
            ms.food_type,
            ms.available_meals,
            ms.serving_start,
            ms.serving_end
        FROM meal_services ms
        JOIN annadan_centres ac
            ON ac.id = ms.centre_id
        WHERE ac.status = 'active'
        AND ms.status = 'available'
        AND ms.service_date = CURDATE()
    """

    params = []

    if city:
        query += " AND ac.city LIKE %s"
        params.append(f"%{city}%")

    if meal_type:
        query += " AND ms.food_type = %s"
        params.append(meal_type)

    if sort_by == 'availability':
        query += " ORDER BY ms.available_meals DESC"
    else:
        query += " ORDER BY ac.id ASC"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()

    services = []

    for row in rows:
        services.append({
            'data': row
        })

    return render_template(
        'warkari/annadan.html',
        services=services,
        city=city,
        meal_type=meal_type,
        sort_by=sort_by
    )

@warkari_bp.route('/map')
def wari_map():

    if 'user_id' not in session or session.get('role') != 'warkari':
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            id,
            centre_name,
            address,
            city,
            latitude,
            longitude,
            status
        FROM annadan_centres
        WHERE status = 'active'
        ORDER BY id
    """)

    rows = cur.fetchall()
    cur.close()

    centres = []

    for row in rows:
        centres.append({
            'id': row[0],
            'name': row[1],
            'address': row[2],
            'city': row[3],
            'latitude': float(row[4]) if row[4] is not None else None,
            'longitude': float(row[5]) if row[5] is not None else None,
            'status': row[6]
        })

    return render_template(
        'warkari/wari_map.html',
        centres=centres
    )