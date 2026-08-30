from flask import Blueprint, jsonify, render_template, request
from app.models.db import mysql
from math import radians, sin, cos, sqrt, asin


# ============================================================
# BLUEPRINT
# ============================================================

public_warkari_bp = Blueprint(
    "public_warkari",
    __name__,
    url_prefix="/warkari/public"
)


# ============================================================
# PUBLIC WARKARI PAGE
# ============================================================

@public_warkari_bp.route("/")
def public_warkari():

    return render_template(
        "public_warkari.html"
    )

# ============================================================
# DISTANCE CALCULATION
# ============================================================

def calculate_distance(lat1, lon1, lat2, lon2):

    try:
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)

    except (TypeError, ValueError):
        return None

    earth_radius_km = 6371.0

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    a = max(0.0, min(1.0, a))

    return earth_radius_km * 2 * asin(sqrt(a))


# ============================================================
# SAFE INTEGER
# ============================================================

def integer_or_zero(value):

    try:

        if value is None:
            return 0

        return int(float(value))

    except (TypeError, ValueError):

        return 0


# ============================================================
# DATABASE
# ============================================================
def fetch_all_centres():

    cursor = mysql.connection.cursor()

    query = """
        SELECT
            ac.id,
            ac.provider_id,
            ac.centre_name,
            ac.address,
            ac.city,
            ac.latitude,
            ac.longitude,
            ac.contact_phone,
            ac.status AS centre_status,

            /* =================================================
               TOTAL AVAILABLE FOOD
               ================================================= */

            COALESCE(
                (
                    SELECT SUM(
                        COALESCE(ms.available_meals, 0)
                    )
                    FROM meal_services ms
                    WHERE ms.centre_id = ac.id

                      /* Today's service or services without date */
                      AND (
                          ms.service_date IS NULL
                          OR DATE(ms.service_date) = CURDATE()
                      )

                      /* Ignore only inactive/closed records */
                      AND (
                          ms.status IS NULL
                          OR LOWER(TRIM(ms.status))
                             NOT IN (
                                 'inactive',
                                 'cancelled',
                                 'completed',
                                 'closed'
                             )
                      )
                ),
                0
            ) AS available_meals,


            /* =================================================
               CURRENT CROWD
               ================================================= */

            COALESCE(
                (
                    SELECT COUNT(DISTINCT cl.varkari_id)
                    FROM crowd_locations cl
                    WHERE cl.centre_id = ac.id
                      AND cl.recorded_at >=
                          NOW() - INTERVAL 60 MINUTE
                      AND cl.movement IN (
                          'stationary',
                          'approaching'
                      )
                ),
                0
            ) AS crowd,


            /* =================================================
               APPROACHING CROWD
               ================================================= */

            COALESCE(
                (
                    SELECT COUNT(DISTINCT cl.varkari_id)
                    FROM crowd_locations cl
                    WHERE cl.centre_id = ac.id
                      AND cl.recorded_at >=
                          NOW() - INTERVAL 60 MINUTE
                      AND cl.movement = 'approaching'
                ),
                0
            ) AS approaching

        FROM annadan_centres ac

        WHERE LOWER(TRIM(ac.status)) = 'active'

        ORDER BY ac.id ASC
    """

    try:

        cursor.execute(query)

        rows = cursor.fetchall()

        print("\n")
        print("=" * 70)
        print("PUBLIC WARKARI CENTRES")
        print("=" * 70)

        for row in rows:

            print(
                f"Centre       : {row[2]}"
            )

            print(
                f"Centre ID    : {row[0]}"
            )

            print(
                f"Meals        : {row[9]}"
            )

            print(
                f"Crowd        : {row[10]}"
            )

            print(
                f"Approaching  : {row[11]}"
            )

            print("-" * 70)

        print("=" * 70)
        print()

        return rows

    except Exception as error:

        print(
            "DATABASE ERROR IN fetch_all_centres():",
            error
        )

        raise

    finally:

        cursor.close()# ============================================================
# ROW TO DICTIONARY
# ============================================================

def row_to_dict(row):

    if isinstance(row, dict):

        return dict(row)

    return {

        "id": row[0],

        "provider_id": row[1],

        "centre_name": row[2],

        "address": row[3],

        "city": row[4],

        "latitude": row[5],

        "longitude": row[6],

        "contact_phone": row[7],

        "centre_status": row[8],

        "available_meals": row[9],

        "crowd": row[10],

        "approaching": row[11]

    }


# ============================================================
# PREPARE CENTRE
# ============================================================

def prepare_centre(row):

    centre = row_to_dict(row)

    available_meals = integer_or_zero(
        centre.get("available_meals")
    )

    crowd = integer_or_zero(
        centre.get("crowd")
    )

    approaching = integer_or_zero(
        centre.get("approaching")
    )

    # ========================================================
    # DEMAND
    # ========================================================

    expected_demand = (
        crowd + approaching
    )

    # ========================================================
    # SHORTAGE
    # ========================================================

    shortage = max(
        expected_demand - available_meals,
        0
    )

    # ========================================================
    # STATUS
    # ========================================================

    if available_meals <= 0:

        status = "unavailable"

    elif shortage > 0:

        status = "high_demand"

    elif available_meals >= expected_demand:

        status = "sufficient"

    else:

        status = "moderate"

    # ========================================================
    # DATA
    # ========================================================

    return {

        "id":
            centre.get("id"),

        "provider_id":
            centre.get("provider_id"),

        "name":
            centre.get("centre_name"),

        "centre_name":
            centre.get("centre_name"),

        "center_name":
            centre.get("centre_name"),

        "address":
            centre.get("address") or "",

        "city":
            centre.get("city") or "",

        "latitude": (

            float(centre["latitude"])

            if centre.get("latitude") is not None

            else None
        ),

        "longitude": (

            float(centre["longitude"])

            if centre.get("longitude") is not None

            else None
        ),

        "contact_phone":
            centre.get("contact_phone") or "",

        "available_meals":
            available_meals,

        "crowd":
            crowd,

        "approaching":
            approaching,

        "expected_demand":
            expected_demand,

        "shortage":
            shortage,

        "status":
            status

    }


# ============================================================
# ALL CENTRES API
# ============================================================

@public_warkari_bp.route(
    "/api/centres",
    methods=["GET"]
)
def all_centres():

    try:

        rows = fetch_all_centres()

        centres = []

        for row in rows:

            centre = prepare_centre(row)

            centre["distance_km"] = None

            centres.append(
                centre
            )

        return jsonify({

            "success": True,

            "count": len(centres),

            "centres": centres,

            "data": centres

        })

    except Exception as error:

        print(
            "PUBLIC WARKARI CENTRES ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "count": 0,

            "centres": [],

            "data": [],

            "error":
                "Unable to load Annadan centres"

        }), 500


# ============================================================
# NEARBY CENTRES API
# ============================================================

@public_warkari_bp.route(
    "/api/nearby-centres",
    methods=["GET"]
)
def nearby_centres():

    try:

        # ====================================================
        # LOCATION
        # ====================================================

        latitude = request.args.get(
            "latitude"
        )

        longitude = request.args.get(
            "longitude"
        )

        if not latitude:

            latitude = request.args.get(
                "lat"
            )

        if not longitude:

            longitude = request.args.get(
                "lon"
            )

        user_lat = None

        user_lon = None

        # ====================================================
        # LATITUDE
        # ====================================================

        if latitude not in (
            None,
            "",
            "null",
            "undefined"
        ):

            user_lat = float(
                latitude
            )

        # ====================================================
        # LONGITUDE
        # ====================================================

        if longitude not in (
            None,
            "",
            "null",
            "undefined"
        ):

            user_lon = float(
                longitude
            )

        # ====================================================
        # RADIUS
        # ====================================================

        radius = request.args.get(
            "radius"
        )

        radius_km = None

        if radius not in (
            None,
            "",
            "null",
            "undefined"
        ):

            radius_km = float(
                radius
            )

            if radius_km < 0:

                radius_km = None

        # ====================================================
        # FETCH CENTRES
        # ====================================================

        rows = fetch_all_centres()

        centres = []

        # ====================================================
        # PROCESS CENTRES
        # ====================================================

        for row in rows:

            centre = prepare_centre(
                row
            )

            centre_lat = centre.get(
                "latitude"
            )

            centre_lon = centre.get(
                "longitude"
            )

            # =================================================
            # DISTANCE
            # =================================================

            if (
                user_lat is not None
                and user_lon is not None
                and centre_lat is not None
                and centre_lon is not None
            ):

                distance = calculate_distance(

                    user_lat,
                    user_lon,

                    centre_lat,
                    centre_lon
                )

                if distance is not None:

                    centre[
                        "distance_km"
                    ] = round(
                        distance,
                        3
                    )

                else:

                    centre[
                        "distance_km"
                    ] = None

                # =============================================
                # OPTIONAL RADIUS FILTER
                # =============================================

                if (
                    radius_km is not None
                    and distance is not None
                    and distance > radius_km
                ):

                    continue

            else:

                centre[
                    "distance_km"
                ] = None

            centres.append(
                centre
            )

        # ====================================================
        # SORT BY DISTANCE
        # ====================================================

        if (
            user_lat is not None
            and user_lon is not None
        ):

            centres.sort(

                key=lambda centre:

                (
                    centre["distance_km"]

                    if centre["distance_km"] is not None

                    else float("inf")
                )
            )

        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({

            "success": True,

            "count": len(centres),

            "centres": centres,

            "data": centres

        })

    except (
        TypeError,
        ValueError
    ) as error:

        print(
            "PUBLIC WARKARI LOCATION ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "count": 0,

            "centres": [],

            "data": [],

            "error":
                "Invalid latitude or longitude"

        }), 400

    except Exception as error:

        print(
            "PUBLIC WARKARI NEARBY ERROR:",
            error
        )

        return jsonify({

            "success": False,

            "count": 0,

            "centres": [],

            "data": [],

            "error":
                "Unable to load nearby Annadan centres"

        }), 500