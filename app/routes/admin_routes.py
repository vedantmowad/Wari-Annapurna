from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    send_file,
    flash
)
from app.models.db import mysql
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)
from io import BytesIO
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required():
    return 'user_id' in session and session.get('role') == 'admin'


def get_prediction_data():
    cur = mysql.connection.cursor()

    query = """
        SELECT
            ac.id,
            ac.centre_name,
            ac.city,

            COALESCE(
                (
                    SELECT SUM(ms.available_meals)
                    FROM meal_services ms
                    WHERE ms.centre_id = ac.id
                    AND ms.status = 'available'
                    AND ms.service_date = CURDATE()
                ),
                0
            ) AS available_meals,

            COALESCE(
                (
                    SELECT COUNT(DISTINCT cl.varkari_id)
                    FROM crowd_locations cl
                    WHERE cl.centre_id = ac.id
                    AND cl.recorded_at >= NOW() - INTERVAL 10 MINUTE
                ),
                0
            ) AS current_crowd,

            COALESCE(
                (
                    SELECT COUNT(DISTINCT cl.varkari_id)
                    FROM crowd_locations cl
                    WHERE cl.centre_id = ac.id
                    AND cl.movement = 'approaching'
                    AND cl.recorded_at >= NOW() - INTERVAL 10 MINUTE
                ),
                0
            ) AS approaching

        FROM annadan_centres ac
        WHERE ac.status = 'active'
        ORDER BY ac.id
    """

    cur.execute(query)
    rows = cur.fetchall()
    cur.close()

    prediction_data = []

    for row in rows:
        centre_id = row[0]
        centre_name = row[1]
        city = row[2]

        available_meals = int(row[3] or 0)
        current_crowd = int(row[4] or 0)
        approaching = int(row[5] or 0)

        predicted_demand = current_crowd + approaching

        meal_shortage = max(
            0,
            predicted_demand - available_meals
        )

        if available_meals > 0:
            pressure = round(
                (predicted_demand / available_meals) * 100
            )
        elif predicted_demand > 0:
            pressure = 100
        else:
            pressure = 0

        if meal_shortage > 0:
            risk = 'Critical'
            recommendation = (
                f'Arrange {meal_shortage} additional meals'
            )
        elif pressure >= 80:
            risk = 'High'
            recommendation = 'Prepare additional meals'
        elif pressure >= 50:
            risk = 'Moderate'
            recommendation = 'Monitor incoming crowd'
        else:
            risk = 'Low'
            recommendation = 'Capacity sufficient'

        prediction_data.append({
            'id': centre_id,
            'name': centre_name,
            'city': city,
            'available_meals': available_meals,
            'current_crowd': current_crowd,
            'approaching': approaching,
            'predicted_demand': predicted_demand,
            'meal_shortage': meal_shortage,
            'pressure': pressure,
            'risk': risk,
            'recommendation': recommendation
        })

    return prediction_data


@admin_bp.route('/dashboard')
def dashboard():
    if not admin_required():
        return redirect(url_for('auth.login'))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM users
    """)
    total_users = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'donor'
    """)
    donors = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'warkari'
    """)
    warkaris = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COUNT(*)
        FROM annadan_centres
        WHERE status = 'active'
    """)
    active_centres = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COALESCE(SUM(available_meals), 0)
        FROM meal_services
        WHERE service_date = CURDATE()
        AND status = 'available'
    """)
    available_meals_today = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COUNT(*)
        FROM meal_services
        WHERE service_date = CURDATE()
        AND status = 'available'
    """)
    active_services = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COUNT(DISTINCT varkari_id)
        FROM crowd_locations
        WHERE recorded_at >= NOW() - INTERVAL 10 MINUTE
    """)
    total_current_crowd = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT COUNT(DISTINCT varkari_id)
        FROM crowd_locations
        WHERE movement = 'approaching'
        AND recorded_at >= NOW() - INTERVAL 10 MINUTE
    """)
    total_approaching = cur.fetchone()[0] or 0

    cur.close()

    active_varkaris = total_current_crowd

    centres = get_prediction_data()

    total_predicted_demand = sum(
        centre['predicted_demand']
        for centre in centres
    )

    total_shortage = sum(
        centre['meal_shortage']
        for centre in centres
    )

    critical_centres = sum(
        1
        for centre in centres
        if centre['risk'] == 'Critical'
    )

    high_centres = sum(
        1
        for centre in centres
        if centre['risk'] == 'High'
    )

    if total_shortage > 0:
        system_status = 'Critical'
        system_status_class = 'danger'
    elif high_centres > 0:
        system_status = 'High Demand'
        system_status_class = 'warning'
    elif total_predicted_demand > 0:
        system_status = 'Moderate'
        system_status_class = 'info'
    else:
        system_status = 'Stable'
        system_status_class = 'success'

    alerts = []

    if critical_centres > 0:
        alerts.append({
            'type': 'danger',
            'title': 'Meal Shortage Detected',
            'message': (
                f'{critical_centres} Annadan centre(s) '
                f'require additional meals.'
            )
        })

    if total_approaching > 0:
        alerts.append({
            'type': 'warning',
            'title': 'Incoming Crowd Detected',
            'message': (
                f'{total_approaching} Varkaris are currently '
                f'approaching Annadan centres.'
            )
        })

    if not alerts:
        alerts.append({
            'type': 'success',
            'title': 'System Stable',
            'message': (
                'Current meal capacity is sufficient for '
                'the detected crowd.'
            )
        })

    return render_template(
        'admin/dashboard.html',

        total_users=total_users,
        active_centres=active_centres,
        available_meals_today=available_meals_today,
        active_varkaris=active_varkaris,

        system_status=system_status,
        system_status_class=system_status_class,

        total_current_crowd=total_current_crowd,
        total_approaching=total_approaching,
        total_predicted_demand=total_predicted_demand,
        total_shortage=total_shortage,

        alerts=alerts,

        centres=centres,
        total_centres=active_centres,

        donors=donors,
        warkaris=warkaris,
        active_services=active_services,
        critical_centres=critical_centres
    )


@admin_bp.route('/users')
def users():
    if not admin_required():
        return redirect(url_for('auth.login'))

    role_filter = request.args.get('role')
    search = request.args.get('search', '').strip()

    query = """
        SELECT
            id,
            full_name,
            email,
            role,
            created_at
        FROM users
        WHERE 1=1
    """

    params = []

    if role_filter:
        query += " AND role = %s"
        params.append(role_filter)

    if search:
        query += """
            AND (
                full_name LIKE %s
                OR email LIKE %s
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value
        ])

    query += " ORDER BY created_at DESC"

    cur = mysql.connection.cursor()
    cur.execute(query, tuple(params))
    users_data = cur.fetchall()
    cur.close()

    return render_template(
        'admin/users.html',
        users=users_data,
        role_filter=role_filter,
        search=search
    )


@admin_bp.route('/centres')
def centres():
    if not admin_required():
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
            contact_phone,
            status,
            created_at
        FROM annadan_centres
        ORDER BY id DESC
    """)

    centres_data = cur.fetchall()
    cur.close()

    return render_template(
        'admin/centres.html',
        centres=centres_data
    )


@admin_bp.route('/meal-services')
def meal_services():
    if not admin_required():
        return redirect(url_for('auth.login'))

    status_filter = request.args.get('status')
    search = request.args.get('search', '').strip()

    query = """
        SELECT
            ms.id,
            ms.centre_id,
            ac.centre_name,
            ms.meal_type,
            ms.available_meals,
            ms.serving_start,
            ms.serving_end,
            ms.service_date,
            ms.status,
            ms.food_type,
            ms.donor_id,
            u.full_name
        FROM meal_services ms
        LEFT JOIN annadan_centres ac
            ON ms.centre_id = ac.id
        LEFT JOIN users u
            ON ms.donor_id = u.id
        WHERE 1=1
    """

    params = []

    if status_filter:
        query += " AND ms.status = %s"
        params.append(status_filter)

    if search:
        query += """
            AND (
                ac.centre_name LIKE %s
                OR ms.meal_type LIKE %s
                OR ms.food_type LIKE %s
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    query += """
        ORDER BY
            ms.service_date DESC,
            ms.serving_start ASC
    """

    cur = mysql.connection.cursor()
    cur.execute(query, tuple(params))
    services = cur.fetchall()
    cur.close()

    return render_template(
        'admin/meal_services.html',
        services=services,
        status_filter=status_filter,
        search=search
    )


@admin_bp.route('/reports')
def reports():
    if not admin_required():
        return redirect(url_for('auth.login'))

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    date_filter = ""
    params = []

    if start_date and end_date:
        date_filter = """
            WHERE service_date BETWEEN %s AND %s
        """
        params = [start_date, end_date]

    cur = mysql.connection.cursor()

    cur.execute(f"""
        SELECT
            COUNT(*),
            COALESCE(SUM(available_meals), 0),
            SUM(
                CASE
                    WHEN status = 'available'
                    THEN 1
                    ELSE 0
                END
            ),
            SUM(
                CASE
                    WHEN status = 'closed'
                    THEN 1
                    ELSE 0
                END
            )
        FROM meal_services
        {date_filter}
    """, tuple(params))

    result = cur.fetchone()

    total_services = result[0] or 0
    total_meals = result[1] or 0
    available_services = result[2] or 0
    closed_services = result[3] or 0

    cur.execute(f"""
        SELECT
            status,
            COUNT(*)
        FROM meal_services
        {date_filter}
        GROUP BY status
    """, tuple(params))

    status_rows = cur.fetchall()

    status_labels = [
        row[0]
        for row in status_rows
    ]

    status_counts = [
        row[1]
        for row in status_rows
    ]

    cur.execute(f"""
        SELECT
            service_date,
            COALESCE(SUM(available_meals), 0)
        FROM meal_services
        {date_filter}
        GROUP BY service_date
        ORDER BY service_date
    """, tuple(params))

    daily_rows = cur.fetchall()

    daily_labels = [
        str(row[0])
        for row in daily_rows
    ]

    daily_meals = [
        row[1]
        for row in daily_rows
    ]

    cur.execute("""
        SELECT
            ac.centre_name,
            COUNT(ms.id),
            COALESCE(SUM(ms.available_meals), 0)
        FROM meal_services ms
        JOIN annadan_centres ac
            ON ms.centre_id = ac.id
        GROUP BY ms.centre_id, ac.centre_name
        ORDER BY SUM(ms.available_meals) DESC
        LIMIT 5
    """)

    top_centres = cur.fetchall()

    cur.execute("""
        SELECT
            ms.id,
            ac.centre_name,
            ms.meal_type,
            ms.available_meals,
            ms.service_date,
            ms.status
        FROM meal_services ms
        LEFT JOIN annadan_centres ac
            ON ms.centre_id = ac.id
        ORDER BY ms.created_at DESC
        LIMIT 10
    """)

    recent = cur.fetchall()

    cur.close()

    return render_template(
        'admin/reports.html',
        total_services=total_services,
        total_meals=total_meals,
        available_services=available_services,
        closed_services=closed_services,
        status_labels=status_labels,
        status_counts=status_counts,
        daily_labels=daily_labels,
        daily_meals=daily_meals,
        top_centres=top_centres,
        recent=recent,
        start_date=start_date,
        end_date=end_date
    )


@admin_bp.route('/reports/print')
def reports_print():
    if not admin_required():
        return redirect(url_for('auth.login'))

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    date_filter = ""
    params = []

    if start_date and end_date:
        date_filter = "WHERE service_date BETWEEN %s AND %s"
        params = [start_date, end_date]

    cur = mysql.connection.cursor()

    cur.execute(f"""
        SELECT
            COUNT(*),
            COALESCE(SUM(available_meals), 0),
            SUM(
                CASE
                    WHEN status = 'available'
                    THEN 1
                    ELSE 0
                END
            ),
            SUM(
                CASE
                    WHEN status = 'closed'
                    THEN 1
                    ELSE 0
                END
            )
        FROM meal_services
        {date_filter}
    """, tuple(params))

    result = cur.fetchone()

    total_services = result[0] or 0
    total_meals = result[1] or 0
    available_services = result[2] or 0
    closed_services = result[3] or 0

    cur.execute(f"""
        SELECT
            status,
            COUNT(*)
        FROM meal_services
        {date_filter}
        GROUP BY status
        ORDER BY COUNT(*) DESC
    """, tuple(params))

    status_rows = cur.fetchall()

    cur.execute(f"""
        SELECT
            service_date,
            COALESCE(SUM(available_meals), 0)
        FROM meal_services
        {date_filter}
        GROUP BY service_date
        ORDER BY service_date
    """, tuple(params))

    daily_rows = cur.fetchall()

    centre_filter = ""
    centre_params = []

    if start_date and end_date:
        centre_filter = """
            WHERE ms.service_date BETWEEN %s AND %s
        """
        centre_params = [start_date, end_date]

    cur.execute(f"""
        SELECT
            ac.centre_name,
            COUNT(ms.id),
            COALESCE(SUM(ms.available_meals), 0)
        FROM meal_services ms
        JOIN annadan_centres ac
            ON ms.centre_id = ac.id
        {centre_filter}
        GROUP BY ms.centre_id, ac.centre_name
        ORDER BY SUM(ms.available_meals) DESC
        LIMIT 5
    """, tuple(centre_params))

    top_centres = cur.fetchall()

    recent_filter = ""
    recent_params = []

    if start_date and end_date:
        recent_filter = """
            WHERE ms.service_date BETWEEN %s AND %s
        """
        recent_params = [start_date, end_date]

    cur.execute(f"""
        SELECT
            ms.id,
            ac.centre_name,
            ms.meal_type,
            ms.available_meals,
            ms.service_date,
            ms.status
        FROM meal_services ms
        LEFT JOIN annadan_centres ac
            ON ms.centre_id = ac.id
        {recent_filter}
        ORDER BY ms.created_at DESC
        LIMIT 10
    """, tuple(recent_params))

    recent = cur.fetchall()

    cur.close()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=8
    )

    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=8
    )

    story = []

    story.append(
        Paragraph(
            "Wari Annapurna",
            title_style
        )
    )

    story.append(
        Paragraph(
            "Admin Reports & Analytics",
            subtitle_style
        )
    )

    period = (
        f"Report Period: {start_date} to {end_date}"
        if start_date and end_date
        else "Report Period: All Available Records"
    )

    story.append(
        Paragraph(
            period,
            subtitle_style
        )
    )

    story.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}",
            subtitle_style
        )
    )

    story.append(
        Paragraph(
            "1. Summary",
            heading_style
        )
    )

    summary_data = [
        ["Metric", "Value"],
        ["Total Meal Services", str(total_services)],
        ["Total Available Meals", str(total_meals)],
        ["Available Services", str(available_services)],
        ["Closed Services", str(closed_services)]
    ]

    table = Table(
        summary_data,
        colWidths=[100 * mm, 70 * mm]
    )

    table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7)
        ])
    )

    story.append(table)

    story.append(
        Paragraph(
            "2. Services by Status",
            heading_style
        )
    )

    status_data = [
        ["Status", "Number of Services"]
    ]

    for row in status_rows:
        status_data.append([
            str(row[0]).capitalize(),
            str(row[1])
        ])

    if len(status_data) == 1:
        status_data.append([
            "No data",
            "0"
        ])

    table = Table(
        status_data,
        colWidths=[100 * mm, 70 * mm]
    )

    table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7)
        ])
    )

    story.append(table)

    story.append(
        Paragraph(
            "3. Daily Meal Availability",
            heading_style
        )
    )

    daily_data = [
        ["Service Date", "Available Meals"]
    ]

    for row in daily_rows:
        daily_data.append([
            str(row[0]),
            str(row[1])
        ])

    if len(daily_data) == 1:
        daily_data.append([
            "No data",
            "0"
        ])

    table = Table(
        daily_data,
        colWidths=[100 * mm, 70 * mm],
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
        ])
    )

    story.append(table)

    story.append(
        Paragraph(
            "4. Top Annadan Centres",
            heading_style
        )
    )

    centre_data = [
        ["Rank", "Centre", "Services", "Available Meals"]
    ]

    for index, row in enumerate(top_centres, start=1):
        centre_data.append([
            str(index),
            str(row[0] or "Unknown"),
            str(row[1]),
            str(row[2])
        ])

    if len(centre_data) == 1:
        centre_data.append([
            "-",
            "No data",
            "0",
            "0"
        ])

    table = Table(
        centre_data,
        colWidths=[
            20 * mm,
            80 * mm,
            35 * mm,
            40 * mm
        ],
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
        ])
    )

    story.append(table)

    story.append(PageBreak())

    story.append(
        Paragraph(
            "5. Recent Meal Services",
            heading_style
        )
    )

    recent_data = [
        ["ID", "Centre", "Meal Type", "Meals", "Date", "Status"]
    ]

    for row in recent:
        recent_data.append([
            str(row[0]),
            str(row[1] or "Unknown"),
            str(row[2] or "-"),
            str(row[3] or 0),
            str(row[4]),
            str(row[5] or "-").capitalize()
        ])

    if len(recent_data) == 1:
        recent_data.append([
            "-",
            "No data",
            "-",
            "0",
            "-",
            "-"
        ])

    table = Table(
        recent_data,
        colWidths=[
            15 * mm,
            45 * mm,
            35 * mm,
            20 * mm,
            30 * mm,
            25 * mm
        ],
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('ALIGN', (5, 1), (5, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
        ])
    )

    story.append(table)

    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            "Wari Annapurna | Admin Reporting System",
            subtitle_style
        )
    )

    doc.build(story)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Wari_Annapurna_Admin_Report.pdf",
        mimetype="application/pdf"
    )

@admin_bp.route("/edit-meals", methods=["GET", "POST"])
def edit_meals():
    if not admin_required():
        return redirect(url_for("auth.login"))

    cursor = mysql.connection.cursor()

    if request.method == "POST":
        centre_id = request.form.get("centre_id")
        meal_service_id = request.form.get("meal_service_id")
        meal_count = request.form.get("meal_count")

        if not centre_id or not meal_service_id or not meal_count:
            flash("Please provide all required details.", "danger")
            cursor.close()
            return redirect(url_for("admin.edit_meals"))

        try:
            meal_count = int(meal_count)

            if meal_count < 0:
                flash("Available meals cannot be negative.", "danger")
                cursor.close()
                return redirect(url_for("admin.edit_meals"))

            cursor.execute(
                """
                SELECT id
                FROM meal_services
                WHERE id = %s
                AND centre_id = %s
                AND service_date = CURDATE()
                """,
                (meal_service_id, centre_id)
            )

            service = cursor.fetchone()

            if not service:
                flash("Invalid meal service selected.", "danger")
                cursor.close()
                return redirect(url_for("admin.edit_meals"))

            cursor.execute(
                """
                UPDATE meal_services
                SET available_meals = %s
                WHERE id = %s
                """,
                (meal_count, meal_service_id)
            )

            mysql.connection.commit()
            flash("Available meals updated successfully.", "success")

        except ValueError:
            mysql.connection.rollback()
            flash("Please enter a valid meal count.", "danger")

        except Exception:
            mysql.connection.rollback()
            flash("Unable to update available meals.", "danger")

        finally:
            cursor.close()

        return redirect(url_for("admin.edit_meals"))

    cursor.execute(
        """
        SELECT
            ms.id,
            ac.centre_name,
            ms.meal_type,
            ms.available_meals,
            ms.serving_start,
            ms.serving_end
        FROM meal_services ms
        JOIN annadan_centres ac
            ON ms.centre_id = ac.id
        WHERE ac.status = 'active'
        AND ms.service_date = CURDATE()
        AND ms.status = 'available'
        ORDER BY ac.centre_name, ms.serving_start
        """
    )

    meal_services_data = cursor.fetchall()

    cursor.close()

    prediction_data = get_prediction_data()

    redistribution = []

    for centre in prediction_data:
        available_meals = centre["available_meals"]
        predicted_demand = centre["predicted_demand"]

        surplus = max(
            available_meals - predicted_demand,
            0
        )

        shortage = max(
            predicted_demand - available_meals,
            0
        )

        redistribution.append({
            "centre_id": centre["id"],
            "centre_name": centre["name"],
            "available_meals": available_meals,
            "predicted_demand": predicted_demand,
            "surplus": surplus,
            "shortage": shortage
        })

    centres = []

    for centre in prediction_data:
        centres.append((
            centre["id"],
            centre["name"],
            centre["available_meals"]
        ))

    return render_template(
        "admin/edit_meal.html",
        centres=centres,
        meal_services=meal_services_data,
        redistribution=redistribution
    )