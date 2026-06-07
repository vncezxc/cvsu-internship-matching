"""
AI-Powered Internship Matching Engine
Uses TF-IDF + cosine similarity to match student resumes with internships.
Computes detailed skills match percentages and AI-powered scoring.
"""

import logging
from math import atan2, cos, exp, radians, sin, sqrt

from .models import MatchModel
from .resume_parser import build_internship_text, parse_student_resume

logger = logging.getLogger(__name__)

FEATURE_ORDER = [
    "tech_match",
    "soft_match",
    "course_match",
    "distance_score",
    "partner_bonus",
]

# ---------- Scoring weights ----------
WEIGHT_RESUME = 0.30
WEIGHT_SKILLS = 0.35
WEIGHT_COURSE = 0.15
WEIGHT_DISTANCE = 0.10
WEIGHT_PARTNER = 0.05
# Reserve 5% for a "coverage penalty" applied at the end


# ---------- Distance helpers ----------

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


# ---------- AI Resume Matching (TF-IDF) ----------

def compute_resume_similarity(resume_text, internship_text):
    """
    Compute cosine similarity between resume text and internship text
    using TF-IDF vectorization. Returns a value between 0.0 and 1.0.
    """
    if not resume_text or not internship_text:
        return 0.0

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),  # Unigrams + bigrams for better matching
            min_df=1,
            max_df=1.0,
        )

        tfidf_matrix = vectorizer.fit_transform([resume_text, internship_text])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

        return float(max(0.0, min(1.0, similarity)))
    except Exception as e:
        logger.warning("TF-IDF matching failed: %s", e)
        return 0.0


# ---------- Skills matching ----------

def compute_detailed_skills_match(profile, internship, resume_keywords=None):
    """
    Compute detailed skills matching between student and internship.

    Returns dict with:
        - tech_match: float 0-1 (technical skills match ratio)
        - soft_match: float 0-1 (soft skills match ratio)
        - matched_skills: list of matched skill names
        - missing_skills: list of missing skill names
        - resume_bonus_skills: list of skills found in resume but not in profile
        - overall_skills_pct: int 0-100
    """
    # Get required skills by type
    req_tech_skills = list(
        internship.required_skills.filter(skill_type="TECHNICAL")
    )
    req_soft_skills = list(
        internship.required_skills.filter(skill_type="SOFT")
    )
    all_required = req_tech_skills + req_soft_skills

    # Get student's profile skills
    student_skill_ids = set(profile.skills.values_list("id", flat=True))
    student_skill_names = set(
        n.lower() for n in profile.skills.values_list("name", flat=True)
    )

    matched_skills = []
    missing_skills = []
    resume_bonus_skills = []

    for skill in all_required:
        if skill.id in student_skill_ids:
            matched_skills.append(skill.name)
        elif resume_keywords and skill.name.lower() in resume_keywords:
            # Skill found in resume text but not in profile — still counts!
            matched_skills.append(skill.name)
            resume_bonus_skills.append(skill.name)
        else:
            # Check for partial keyword match in resume
            skill_words = set(skill.name.lower().split())
            if resume_keywords and skill_words and skill_words.issubset(resume_keywords):
                matched_skills.append(skill.name)
                resume_bonus_skills.append(skill.name)
            else:
                missing_skills.append(skill.name)

    # Calculate match ratios
    req_tech_ids = {s.id for s in req_tech_skills}
    req_soft_ids = {s.id for s in req_soft_skills}

    # For tech/soft match, count profile + resume matches
    matched_names_lower = {n.lower() for n in matched_skills}
    tech_matched = sum(
        1 for s in req_tech_skills if s.name.lower() in matched_names_lower
    )
    soft_matched = sum(
        1 for s in req_soft_skills if s.name.lower() in matched_names_lower
    )

    tech_match = tech_matched / len(req_tech_skills) if req_tech_skills else 0.5
    soft_match = soft_matched / len(req_soft_skills) if req_soft_skills else 0.5

    total_required = len(all_required)
    overall_pct = int(round(len(matched_skills) / total_required * 100)) if total_required else 50

    return {
        "tech_match": tech_match,
        "soft_match": soft_match,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "resume_bonus_skills": resume_bonus_skills,
        "overall_skills_pct": overall_pct,
    }


# ---------- Feature building ----------

def build_features(profile, internship, distance_km, resume_data=None):
    """
    Build feature dict for scoring. Now includes AI resume matching.
    """
    # Parse resume if not already done
    if resume_data is None:
        resume_data = parse_student_resume(profile)

    resume_keywords = resume_data.get("keywords", set())

    # Detailed skills match (with resume keyword bonus)
    skills_result = compute_detailed_skills_match(profile, internship, resume_keywords)

    tech_match = skills_result["tech_match"]
    soft_match = skills_result["soft_match"]

    # Course match
    course_match = 1.0 if profile.course in internship.recommended_courses.all() else 0.0

    # Distance score — use a smoother curve
    # If location data is missing, treat as neutral (0.5) rather than penalizing
    if distance_km is None:
        distance_score = 0.5  # neutral when unknown
    else:
        # Exponential decay: close = high score, >50km = very low
        distance_score = max(0.0, exp(-distance_km / 25.0))

    # Partner bonus — scaled to 0.5 so it doesn't dominate
    partner_bonus = 0.5 if internship.company.is_partner else 0.0

    # AI Resume similarity (TF-IDF)
    resume_match = 0.0
    if resume_data.get("has_resume"):
        internship_text = build_internship_text(internship)
        resume_match = compute_resume_similarity(
            resume_data["cleaned_text"], internship_text
        )

    return {
        "tech_match": tech_match,
        "soft_match": soft_match,
        "course_match": course_match,
        "distance_score": distance_score,
        "partner_bonus": partner_bonus,
        "resume_match": resume_match,
        "skills_result": skills_result,
    }


# ---------- Scoring ----------

def score_rules(features):
    """Legacy rule-based score (kept as fallback)."""
    return round(
        features["tech_match"] * 50
        + features["soft_match"] * 20
        + features["course_match"] * 20
        + features["distance_score"] * 10
    )


def score_with_model(features):
    """Score using trained logistic regression model (if available)."""
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


def compute_ai_score(features):
    """
    Compute the AI-powered composite score.
    Combines resume similarity, skills match, course, distance, and partner bonus.
    Produces more honest, differentiated scores.
    """
    resume_match = features.get("resume_match", 0.0)
    skills_result = features.get("skills_result", {})
    overall_skills = skills_result.get("overall_skills_pct", 0) / 100.0

    course_match = features["course_match"]
    distance_score = features["distance_score"]
    partner_bonus = features["partner_bonus"]

    has_resume = resume_match > 0

    if has_resume:
        # Full AI scoring with all components
        composite = (
            resume_match * WEIGHT_RESUME
            + overall_skills * WEIGHT_SKILLS
            + course_match * WEIGHT_COURSE
            + distance_score * WEIGHT_DISTANCE
            + partner_bonus * WEIGHT_PARTNER
        )
    else:
        # No resume — skills and course carry the weight, but cap lower
        # because we have less confidence without resume data
        composite = (
            overall_skills * 0.50
            + course_match * 0.25
            + distance_score * WEIGHT_DISTANCE
            + partner_bonus * WEIGHT_PARTNER
        )
        # Apply a confidence penalty: without a resume we cap at 75%
        composite = min(composite, 0.75)

    # Apply a coverage penalty: if skills are 0%, heavily penalize
    if overall_skills == 0 and len(skills_result.get("missing_skills", [])) > 0:
        composite *= 0.5

    # Convert to percentage and apply non-linear scaling
    # This spreads scores out more naturally instead of clustering around 40-60%
    raw_pct = composite * 100

    # Ensure minimum floor of 5% when there's at least some data
    if raw_pct < 5 and (overall_skills > 0 or course_match > 0 or resume_match > 0):
        raw_pct = 5

    return int(round(min(raw_pct, 100)))


def generate_ai_summary(features, internship):
    """
    Generate a human-readable AI analysis summary for the match.
    """
    resume_match = features.get("resume_match", 0.0)
    skills_result = features.get("skills_result", {})
    matched = skills_result.get("matched_skills", [])
    missing = skills_result.get("missing_skills", [])
    resume_bonus = skills_result.get("resume_bonus_skills", [])
    course_match = features["course_match"]
    distance_score = features.get("distance_score", 0.0)

    parts = []

    # Resume analysis
    if resume_match > 0:
        pct = int(round(resume_match * 100))
        if pct >= 70:
            parts.append(f"Your resume is an excellent match ({pct}% similarity) with this position.")
        elif pct >= 40:
            parts.append(f"Your resume shows good alignment ({pct}% similarity) with this role.")
        elif pct >= 15:
            parts.append(f"Your resume has some relevant content ({pct}% similarity) for this position.")
        else:
            parts.append(f"Your resume has limited overlap ({pct}% similarity) with this role's requirements.")
    else:
        parts.append("Upload your resume/CV to get a more accurate AI match analysis.")

    # Skills analysis
    total_required = len(matched) + len(missing)
    if total_required > 0:
        skills_pct = int(round(len(matched) / total_required * 100))
        if matched and skills_pct >= 70:
            parts.append(f"Strong skills match ({len(matched)}/{total_required}): {', '.join(matched[:4])}.")
        elif matched:
            parts.append(f"Partial skills match ({len(matched)}/{total_required}): {', '.join(matched[:4])}.")
        else:
            parts.append(f"No matching skills found out of {total_required} required.")

    if resume_bonus:
        parts.append(f"AI found additional skills in your resume: {', '.join(resume_bonus[:3])}.")

    if missing:
        top_missing = missing[:3]
        parts.append(f"Consider developing: {', '.join(top_missing)}.")

    # Course analysis
    if course_match >= 1.0:
        parts.append("Your course is a recommended fit for this internship.")
    else:
        parts.append("Your course is not listed as recommended for this position.")

    return " ".join(parts)


# ---------- Main scoring function ----------

def score_internship(profile, internship):
    """
    AI-powered internship scoring.

    Returns a comprehensive dict with:
        - score: Overall match percentage (0-100)
        - resume_match_pct: AI resume similarity percentage
        - skills_match_pct: Overall skills match percentage
        - tech_pct: Technical skills match percentage
        - soft_pct: Soft skills match percentage
        - course_pct: Course match percentage
        - map_pct: Location proximity percentage
        - matched_skills: List of matched skill names
        - missing_skills: List of missing skill names
        - resume_bonus_skills: Skills found in resume but not in profile
        - ai_summary: Human-readable AI analysis text
        - has_resume: Whether the student has a parseable resume
        - distance_km: Distance in km (or None)
        - rule_score: Legacy rule-based score
        - model_score: ML model score (if available)
        - features: Raw feature dict
    """
    # Parse resume once (reused across feature building)
    resume_data = parse_student_resume(profile)

    distance_km = compute_distance_km(profile, internship)
    features = build_features(profile, internship, distance_km, resume_data)

    skills_result = features["skills_result"]

    tech_pct = int(round(features["tech_match"] * 100))
    soft_pct = int(round(features["soft_match"] * 100))
    course_pct = int(round(features["course_match"] * 100))
    map_pct = int(round(features["distance_score"] * 100))
    resume_match_pct = int(round(features["resume_match"] * 100))

    # Compute scores
    rule_score = score_rules(features)
    model_score = score_with_model(features)
    ai_score = compute_ai_score(features)

    # Use AI score as primary, fall back to model or rules
    if model_score is not None:
        final_score = max(ai_score, model_score)
    else:
        final_score = ai_score

    # Generate AI summary
    ai_summary = generate_ai_summary(features, internship)

    return {
        "score": final_score,
        "rule_score": rule_score,
        "model_score": model_score,
        "ai_score": ai_score,
        "distance_km": round(distance_km, 1) if distance_km is not None else None,
        "tech_pct": tech_pct,
        "soft_pct": soft_pct,
        "course_pct": course_pct,
        "map_pct": map_pct,
        "resume_match_pct": resume_match_pct,
        "skills_match_pct": skills_result["overall_skills_pct"],
        "matched_skills": skills_result["matched_skills"],
        "missing_skills": skills_result["missing_skills"],
        "resume_bonus_skills": skills_result["resume_bonus_skills"],
        "ai_summary": ai_summary,
        "has_resume": resume_data.get("has_resume", False),
        "features": features,
    }
