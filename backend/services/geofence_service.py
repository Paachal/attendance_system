import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance in meters between two GPS points
    using the Haversine formula.
    """
    R = 6_371_000  # Earth radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def check_geofence(
    student_lat: float,
    student_lon: float,
    session_lat: float,
    session_lon: float,
    radius_meters: float,
) -> dict:
    """
    Checks whether a student's coordinates fall within the session's
    allowed geofence radius.

    Returns:
        {
            inside:   bool,
            distance: float,   # actual distance in meters
            radius:   float,   # allowed radius
            message:  str,
        }
    """
    distance = haversine_distance(
        student_lat, student_lon,
        session_lat, session_lon,
    )

    inside = distance <= radius_meters

    if inside:
        message = f"Within range — {distance:.1f}m from classroom"
    else:
        overshoot = distance - radius_meters
        message = (
            f"Outside attendance zone — you are {distance:.1f}m away "
            f"({overshoot:.1f}m beyond the allowed {radius_meters:.0f}m radius)"
        )

    return {
        "inside":   inside,
        "distance": round(distance, 2),
        "radius":   radius_meters,
        "message":  message,
    }