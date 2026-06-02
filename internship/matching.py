from math import atan2, cos, exp, radians, sin, sqrt

from .models import MatchModel

FEATURE_ORDER = [
    "tech_match",
    "soft_match",
    "course_match",
    "distance_score",
    "partner_bonus",
]


def haversine(lat1, lon1, lat2, lon2):
    r_km = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r_km * c


def compute_distance_km(profile, internship):
    company = internship.company
    if not (company.latitude and company.longitude and profile.latitude and profile.longitude):
        return None
    try:
        return haversine(
            float(company.latitude),
            float(company.longitude),
            float(profile.latitude),
            float(profile.longitude),
        )
    except Exception:
        return None


def build_features(profile, internship, distance_km):
    req_tech = set(
        internship.required_skills.filter(skill_type="TECHNICAL").values_list("id", flat=True)
    )
    stu_tech = set(profile.skills.filter(skill_type="TECHNICAL").values_list("id", flat=True))
    tech_match = len(req_tech & stu_tech) / len(req_tech) if req_tech else 1.0

    req_soft = set(
        internship.required_skills.filter(skill_type="SOFT").values_list("id", flat=True)
    )
    stu_soft = set(profile.skills.filter(skill_type="SOFT").values_list("id", flat=True))
    soft_match = len(req_soft & stu_soft) / len(req_soft) if req_soft else 1.0

    course_match = 1.0 if profile.course in internship.recommended_courses.all() else 0.0

    if distance_km is None:
        distance_score = 0.0
    else:
        capped = min(distance_km, 50.0)
        distance_score = max(0.0, 1.0 - (capped / 50.0))

    partner_bonus = 1.0 if internship.company.is_partner else 0.0

    return {
        "tech_match": tech_match,
        "soft_match": soft_match,
        "course_match": course_match,
        "distance_score": distance_score,
        "partner_bonus": partner_bonus,
    }


def score_rules(features):
    return round(
        features["tech_match"] * 50
        + features["soft_match"] * 20
        + features["course_match"] * 20
        + features["distance_score"] * 10
    )


def score_with_model(features):
    model = MatchModel.objects.order_by("-created_at").first()
    if not model:
        return None

    if model.feature_order != FEATURE_ORDER:
        return None

    coef = model.coef
    intercept = model.intercept
    z = intercept
    for idx, name in enumerate(FEATURE_ORDER):
        z += coef[idx] * features[name]

    prob = 1.0 / (1.0 + exp(-z))
    return int(round(prob * 100))


def score_internship(profile, internship):
    distance_km = compute_distance_km(profile, internship)
    features = build_features(profile, internship, distance_km)

    tech_pct = int(round(features["tech_match"] * 100))
    soft_pct = int(round(features["soft_match"] * 100))
    course_pct = int(round(features["course_match"] * 100))
    map_pct = int(round(features["distance_score"] * 100))

    rule_score = score_rules(features)
    model_score = score_with_model(features)

    return {
        "score": model_score if model_score is not None else rule_score,
        "rule_score": rule_score,
        "model_score": model_score,
        "distance_km": round(distance_km, 1) if distance_km is not None else None,
        "tech_pct": tech_pct,
        "soft_pct": soft_pct,
        "course_pct": course_pct,
        "map_pct": map_pct,
        "features": features,
    }
