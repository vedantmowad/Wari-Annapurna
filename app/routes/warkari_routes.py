from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from app.models.db import mysql
import math

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

@warkari_bp.route('/centre/<int:centre_id>')
def centre_details(centre_id):

    if 'user_id' not in session or session.get('role') != 'warkari':
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            ac.id,
            ac.centre_name,
            ac.address,
            ac.city,
            ac.latitude,
            ac.longitude,
            ac.status
        FROM annadan_centres ac
        WHERE ac.id = %s
        AND ac.status = 'active'
    """, (centre_id,))

    centre = cur.fetchone()

    if not centre:
        cur.close()
        return redirect(url_for('warkari.annadan'))

    cur.execute("""
        SELECT
            ms.id,
            ms.meal_type,
            ms.available_meals,
            ms.serving_start,
            ms.serving_end,
            ms.service_date,
            ms.status,
            ms.food_type
        FROM meal_services ms
        WHERE ms.centre_id = %s
        AND ms.service_date = CURDATE()
        ORDER BY
            CASE
                WHEN ms.status = 'available'
                AND CURTIME() BETWEEN ms.serving_start AND ms.serving_end
                THEN 0

                WHEN ms.status = 'available'
                AND ms.serving_start > CURTIME()
                THEN 1

                WHEN ms.status = 'available'
                THEN 2

                ELSE 3
            END,
            ms.serving_start ASC
    """, (centre_id,))

    meal_services = cur.fetchall()

    meal_type = ''
    available_meals = 0
    serving_start = None
    serving_end = None
    meal_status = 'unavailable'
    food_type = ''

    if meal_services:

        selected_meal = meal_services[0]

        meal_type = selected_meal[1] or ''
        available_meals = int(selected_meal[2] or 0)
        serving_start = selected_meal[3]
        serving_end = selected_meal[4]
        meal_status = selected_meal[6] or 'unavailable'
        food_type = selected_meal[7] or ''

    cur.execute("""
        SELECT COUNT(DISTINCT varkari_id)
        FROM crowd_locations
        WHERE centre_id = %s
        AND recorded_at >= NOW() - INTERVAL 10 MINUTE
    """, (centre_id,))

    current_crowd = int(cur.fetchone()[0] or 0)

    cur.execute("""
        SELECT COUNT(DISTINCT varkari_id)
        FROM crowd_locations
        WHERE centre_id = %s
        AND movement = 'approaching'
        AND recorded_at >= NOW() - INTERVAL 10 MINUTE
    """, (centre_id,))

    approaching = int(cur.fetchone()[0] or 0)

    cur.close()

    expected_demand = current_crowd + approaching

    shortage = max(
        0,
        expected_demand - available_meals
    )

    centre_data = {
        'id': centre[0],
        'name': centre[1] or '',
        'address': centre[2] or '',
        'city': centre[3] or '',
        'latitude': float(centre[4]) if centre[4] is not None else 0.0,
        'longitude': float(centre[5]) if centre[5] is not None else 0.0,
        'status': centre[6] or 'inactive',

        'meal_type': meal_type,
        'available_meals': available_meals,
        'serving_start': serving_start,
        'serving_end': serving_end,
        'meal_status': meal_status,
        'food_type': food_type,

        'current_crowd': current_crowd,
        'approaching': approaching,
        'expected_demand': expected_demand,
        'shortage': shortage,

        'meal_services': meal_services
    }

    return render_template(
        'warkari/annadan_detail.html',
        centre=centre_data
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

@warkari_bp.route('/api/nearby-centres')
def nearby_centres():

    if 'user_id' not in session or session.get('role') != 'warkari':
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401

    user_lat = request.args.get('latitude', type=float)
    user_lon = request.args.get('longitude', type=float)

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            ac.id,
            ac.centre_name,
            ac.address,
            ac.city,
            ac.latitude,
            ac.longitude,

            COALESCE(
                SUM(
                    CASE
                        WHEN ms.status = 'available'
                        AND ms.service_date = CURDATE()
                        THEN ms.available_meals
                        ELSE 0
                    END
                ),
                0
            ) AS available_meals

        FROM annadan_centres ac

        LEFT JOIN meal_services ms
            ON ms.centre_id = ac.id

        WHERE ac.status = 'active'

        GROUP BY
            ac.id,
            ac.centre_name,
            ac.address,
            ac.city,
            ac.latitude,
            ac.longitude

        ORDER BY ac.id
    """)

    rows = cur.fetchall()

    centres = []

    for row in rows:

        centre_id = row[0]
        latitude = float(row[4]) if row[4] is not None else None
        longitude = float(row[5]) if row[5] is not None else None
        available_meals = int(row[6] or 0)

        cur.execute("""
            SELECT COUNT(DISTINCT varkari_id)
            FROM crowd_locations
            WHERE centre_id = %s
            AND recorded_at >= NOW() - INTERVAL 10 MINUTE
        """, (centre_id,))

        crowd = cur.fetchone()[0] or 0

        cur.execute("""
            SELECT COUNT(DISTINCT varkari_id)
            FROM crowd_locations
            WHERE centre_id = %s
            AND movement = 'approaching'
            AND recorded_at >= NOW() - INTERVAL 10 MINUTE
        """, (centre_id,))

        approaching = cur.fetchone()[0] or 0

        expected_demand = crowd + approaching
        shortage = max(0, expected_demand - available_meals)

        if expected_demand == 0:
            status = 'sufficient'
        elif available_meals >= expected_demand:
            status = 'sufficient'
        elif available_meals >= expected_demand * 0.5:
            status = 'moderate'
        else:
            status = 'high_demand'

        distance = None

        if (
            user_lat is not None
            and user_lon is not None
            and latitude is not None
            and longitude is not None
        ):
            distance = calculate_distance(
                user_lat,
                user_lon,
                latitude,
                longitude
            )

        centres.append({
            'id': centre_id,
            'name': row[1],
            'address': row[2],
            'city': row[3],
            'latitude': latitude,
            'longitude': longitude,
            'available_meals': available_meals,
            'crowd': int(crowd),
            'approaching': int(approaching),
            'expected_demand': int(expected_demand),
            'shortage': int(shortage),
            'distance_km': distance,
            'status': status
        })

    cur.close()

    if user_lat is not None and user_lon is not None:
        centres.sort(
            key=lambda x: (
                x['distance_km']
                if x['distance_km'] is not None
                else 999999
            )
        )

    return jsonify(centres)


@warkari_bp.route('/api/centres')
def api_centres():

    if 'user_id' not in session or session.get('role') != 'warkari':
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401

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

    return jsonify({
        'success': True,
        'count': len(centres),
        'centres': centres
    })


@warkari_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.landing'))
