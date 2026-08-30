from math import radians, sin, cos, sqrt, asin
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from app.models.db import mysql

donor_bp = Blueprint('donor', __name__, url_prefix='/donor')


def calculate_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return 6371 * c


def get_donation_recommendations():
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            ac.id,
            ac.centre_name,
            ac.address,
            ac.city,
            ac.latitude,
            ac.longitude,
            COALESCE(SUM(
                CASE
                    WHEN ms.status = 'available'
                    AND ms.service_date = CURDATE()
                    THEN ms.available_meals
                    ELSE 0
                END
            ), 0) AS available_meals
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
    """)

    centres = cur.fetchall()
    recommendations = []

    for centre in centres:
        centre_id = centre[0]
        centre_name = centre[1]
        address = centre[2]
        city = centre[3]
        latitude = centre[4]
        longitude = centre[5]
        available_meals = int(centre[6] or 0)

        cur.execute("""
            SELECT
                COUNT(DISTINCT varkari_id),
                COUNT(DISTINCT CASE
                    WHEN movement = 'approaching'
                    THEN varkari_id
                END),
                COUNT(DISTINCT CASE
                    WHEN movement = 'leaving'
                    THEN varkari_id
                END),
                COUNT(DISTINCT CASE
                    WHEN movement = 'stationary'
                    THEN varkari_id
                END)
            FROM crowd_locations
            WHERE centre_id = %s
            AND recorded_at >= NOW() - INTERVAL 60 MINUTE
        """, (centre_id,))

        crowd_data = cur.fetchone()

        crowd = int(crowd_data[0] or 0)
        approaching = int(crowd_data[1] or 0)
        leaving = int(crowd_data[2] or 0)
        stationary = int(crowd_data[3] or 0)

        expected_demand = crowd +  approaching
        shortage = max(0, expected_demand - available_meals)

        if shortage <= 0:
            continue

        shortage_ratio = (
            shortage / expected_demand
            if expected_demand > 0
            else 0
        )

        crowd_pressure = (
            approaching / expected_demand
            if expected_demand > 0
            else 0
        )

        priority_score = (
            shortage_ratio * 70
            + crowd_pressure * 30
        )

        if priority_score >= 70:
            status = 'critical'
        elif priority_score >= 45:
            status = 'high'
        else:
            status = 'moderate'

        recommendations.append({
            'centre_id': centre_id,
            'centre_name': centre_name,
            'address': address,
            'city': city,
            'latitude': float(latitude) if latitude is not None else None,
            'longitude': float(longitude) if longitude is not None else None,
            'available_meals': available_meals,
            'current_crowd': crowd,
            'approaching': approaching,
            'leaving': leaving,
            'stationary': stationary,
            'expected_demand': expected_demand,
            'shortage': shortage,
            'shortage_percentage': round(shortage_ratio * 100, 2),
            'priority_score': round(priority_score, 2),
            'status': status
        })

    cur.close()

    recommendations.sort(
        key=lambda x: x['priority_score'],
        reverse=True
    )

    return recommendations


@donor_bp.route('/api/donation-recommendations', methods=['GET'])
def donation_recommendations():
    if 'user_id' not in session or session.get('role') != 'donor':
        return jsonify({'error': 'Unauthorized'}), 401

    recommendations = get_donation_recommendations()

    return jsonify({
        'success': True,
        'count': len(recommendations),
        'recommendations': recommendations
    })


@donor_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.landing'))


@donor_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'donor':
        return redirect(url_for('auth.login'))

    donor_id = session['user_id']
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT DISTINCT ac.id, ac.centre_name
        FROM meal_services ms
        JOIN annadan_centres ac ON ms.centre_id = ac.id
        WHERE ms.donor_id = %s
        ORDER BY ac.id DESC
    """, (donor_id,))
    centres = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*)
        FROM meal_services
        WHERE donor_id = %s
    """, (donor_id,))
    total_services = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COALESCE(SUM(available_meals), 0)
        FROM meal_services
        WHERE donor_id = %s
    """, (donor_id,))
    total_meals = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COALESCE(SUM(available_meals), 0)
        FROM meal_services
        WHERE donor_id = %s
        AND status = 'available'
    """, (donor_id,))
    available_meals = cur.fetchone()[0] or 0

    people_fed = int(total_meals)

    cur.execute("""
        SELECT
            ms.id,
            ac.centre_name,
            ms.meal_type,
            ms.food_type,
            ms.available_meals,
            ms.serving_start,
            ms.serving_end,
            ms.service_date,
            ms.status
        FROM meal_services ms
        JOIN annadan_centres ac ON ms.centre_id = ac.id
        WHERE ms.donor_id = %s
        ORDER BY ms.service_date DESC, ms.created_at DESC
        LIMIT 5
    """, (donor_id,))
    recent_services = cur.fetchall()

    cur.close()

    recommendations = get_donation_recommendations()
    top_recommendation = recommendations[0] if recommendations else None

    return render_template(
        'donor/dashboard.html',
        total_services=total_services,
        total_meals=total_meals,
        available_meals=available_meals,
        people_fed=people_fed,
        centres=centres,
        recent_services=recent_services,
        recommendations=recommendations[:5],
        top_recommendation=top_recommendation
    )


@donor_bp.route('/add-donation', methods=['GET', 'POST'])
def add_donation():
    if 'user_id' not in session or session.get('role') != 'donor':
        return redirect(url_for('auth.login'))

    donor_id = session['user_id']
    cursor = mysql.connection.cursor()

    recommendations = get_donation_recommendations()

    cursor.execute("""
        SELECT id, centre_name
        FROM annadan_centres
        WHERE status = 'active'
        ORDER BY id DESC
    """)
    centres = cursor.fetchall()

    if request.method == 'POST':
        centre_id = request.form.get('centre_id')
        meal_name = request.form.get('meal_name')
        food_type = request.form.get('food_type')
        meal_count = request.form.get('meal_count')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        service_date = request.form.get('service_date')
        status = request.form.get('status', 'available')

        if not centre_id:
            flash('Please select an Annadan centre.', 'danger')
            cursor.close()
            return redirect(url_for('donor.add_donation'))

        cursor.execute("""
            SELECT id
            FROM users
            WHERE id = %s AND role = 'donor'
        """, (donor_id,))

        if not cursor.fetchone():
            cursor.close()
            flash('Invalid donor account.', 'danger')
            return redirect(url_for('auth.login'))

        cursor.execute("""
            SELECT id
            FROM annadan_centres
            WHERE id = %s
            AND status = 'active'
        """, (centre_id,))

        if not cursor.fetchone():
            cursor.close()
            flash('Invalid Annadan centre selected.', 'danger')
            return redirect(url_for('donor.add_donation'))

        if not meal_count or int(meal_count) <= 0:
            cursor.close()
            flash('Please enter a valid meal quantity.', 'danger')
            return redirect(url_for('donor.add_donation'))

        cursor.execute("""
            INSERT INTO meal_services
            (
                donor_id,
                centre_id,
                meal_type,
                food_type,
                available_meals,
                serving_start,
                serving_end,
                service_date,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            donor_id,
            centre_id,
            meal_name,
            food_type,
            meal_count,
            start_time,
            end_time,
            service_date,
            status
        ))

        mysql.connection.commit()
        cursor.close()

        flash('Meal donation registered successfully.', 'success')
        return redirect(url_for('donor.dashboard'))

    cursor.close()

    return render_template(
        'donor/add_donation.html',
        centres=centres,
        recommendations=recommendations
    )


@donor_bp.route('/impact')
def impact():
    if 'user_id' not in session or session.get('role') != 'donor':
        return redirect(url_for('auth.login'))

    donor_id = session['user_id']
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT DISTINCT ac.id, ac.centre_name
        FROM annadan_centres ac
        JOIN meal_services ms ON ms.centre_id = ac.id
        WHERE ms.donor_id = %s
        ORDER BY ac.id DESC
    """, (donor_id,))
    centres = cur.fetchall()

    date_filter = ""
    date_params = []

    if start_date and end_date:
        date_filter = "AND ms.service_date BETWEEN %s AND %s"
        date_params = [start_date, end_date]

    params = [donor_id] + date_params

    cur.execute(f"""
        SELECT
            COUNT(*),
            COALESCE(SUM(ms.available_meals), 0),
            COALESCE(
                SUM(
                    CASE
                        WHEN ms.status = 'available'
                        THEN ms.available_meals
                        ELSE 0
                    END
                ),
                0
            )
        FROM meal_services ms
        WHERE ms.donor_id = %s
        {date_filter}
    """, tuple(params))

    result = cur.fetchone()

    total_services = result[0] or 0
    total_meals = result[1] or 0
    available_meals = result[2] or 0
    people_fed = int(total_meals)

    params = [donor_id] + date_params

    cur.execute(f"""
        SELECT ms.status, COUNT(*)
        FROM meal_services ms
        WHERE ms.donor_id = %s
        {date_filter}
        GROUP BY ms.status
    """, tuple(params))
    status_data = cur.fetchall()

    params = [donor_id] + date_params

    cur.execute(f"""
        SELECT
            ms.meal_type,
            COALESCE(SUM(ms.available_meals), 0)
        FROM meal_services ms
        WHERE ms.donor_id = %s
        {date_filter}
        GROUP BY ms.meal_type
        ORDER BY SUM(ms.available_meals) DESC
    """, tuple(params))
    meal_type_data = cur.fetchall()

    params = [donor_id] + date_params

    cur.execute(f"""
        SELECT
            ms.service_date,
            COALESCE(SUM(ms.available_meals), 0)
        FROM meal_services ms
        WHERE ms.donor_id = %s
        {date_filter}
        GROUP BY ms.service_date
        ORDER BY ms.service_date
    """, tuple(params))
    daily_data = cur.fetchall()

    params = [donor_id] + date_params

    cur.execute(f"""
        SELECT
            CONCAT(
                YEAR(ms.service_date),
                '-W',
                LPAD(WEEK(ms.service_date, 1), 2, '0')
            ),
            COALESCE(SUM(ms.available_meals), 0)
        FROM meal_services ms
        WHERE ms.donor_id = %s
        {date_filter}
        GROUP BY YEAR(ms.service_date), WEEK(ms.service_date, 1)
        ORDER BY YEAR(ms.service_date), WEEK(ms.service_date, 1)
    """, tuple(params))
    weekly_data = cur.fetchall()

    params = [donor_id] + date_params

    cur.execute(f"""
        SELECT
            DATE_FORMAT(ms.service_date, '%%b %%Y'),
            COALESCE(SUM(ms.available_meals), 0)
        FROM meal_services ms
        WHERE ms.donor_id = %s
        {date_filter}
        GROUP BY YEAR(ms.service_date), MONTH(ms.service_date)
        ORDER BY YEAR(ms.service_date), MONTH(ms.service_date)
    """, tuple(params))
    monthly_data = cur.fetchall()

    params = [donor_id] + date_params

    cur.execute(f"""
        SELECT
            ms.id,
            ac.centre_name,
            ms.meal_type,
            ms.food_type,
            ms.available_meals,
            ms.serving_start,
            ms.serving_end,
            ms.service_date,
            ms.status
        FROM meal_services ms
        JOIN annadan_centres ac
            ON ms.centre_id = ac.id
        WHERE ms.donor_id = %s
        {date_filter}
        ORDER BY ms.service_date DESC, ms.serving_start DESC
    """, tuple(params))
    table_data = cur.fetchall()

    cur.close()

    return render_template(
        'donor/impact.html',
        total_services=total_services,
        total_meals=total_meals,
        available_meals=available_meals,
        people_fed=people_fed,
        status_data=status_data,
        meal_type_data=meal_type_data,
        daily_data=daily_data,
        weekly_data=weekly_data,
        monthly_data=monthly_data,
        table_data=table_data,
        centres=centres,
        start_date=start_date,
        end_date=end_date
    )