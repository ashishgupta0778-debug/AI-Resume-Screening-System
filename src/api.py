from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from pathlib import Path
from typing import List, Optional

import os
import re
import csv
import io
import math
import json
import time
import tempfile
from collections import Counter
from datetime import datetime

from src.db import get_db, hash_password, verify_password, init_db
from src.auth import create_session, validate_session, delete_session, get_current_user
from src.resume_extractor import (
    extract_resume_text,
    extract_skills,
    extract_experience,
    extract_experience_years,
    extract_education,
    extract_candidate_profile,
    SKILLS_CATALOG,
    TECHNICAL_SKILLS,
    SOFT_SKILLS
)

# Initialize database tables on startup
init_db()

# =============================
# FASTAPI APP
# =============================

app = FastAPI(
    title="AI Resume Screening and Candidate Shortlisting System",
    version="2.0.0",
    description="Professional AI-driven recruitment and candidate ranking platform."
)

# =============================
# CORS MIDDLEWARE
# =============================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# PATH CONSTANTS
# =============================

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
DEFAULT_JD_FILE = BASE_DIR / "data" / "jobs" / "software_developer.txt"

if DEFAULT_JD_FILE.exists():
    with open(DEFAULT_JD_FILE, "r", encoding="utf-8") as file:
        default_job_description = file.read().lower()
else:
    default_job_description = "software developer python java sql machine learning 2 years experience bachelor degree"

required_skills = list(SKILLS_CATALOG)


# =============================
# Pydantic Schemas
# =============================

class LoginRequest(BaseModel):
    email: str
    password: str


class JobCreateRequest(BaseModel):
    title: str
    description: str
    required_skills: Optional[List[str]] = []
    preferred_skills: Optional[List[str]] = []
    min_experience: Optional[int] = 0
    education: Optional[str] = "Not Specified"


class StatusUpdateRequest(BaseModel):
    status: str


class SkillSearchRequest(BaseModel):
    skills: List[str]
    mode: str = "ANY"  # "ANY" or "ALL"
    min_score: Optional[float] = 0.0
    status: Optional[str] = "all"


# =============================
# Helper: Extract JD Requirements
# =============================

def extract_jd_skills(job_description):
    return extract_skills(job_description, custom_skills=required_skills)


def extract_required_experience(job_description):
    pattern = r"\b(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b"
    match = re.search(pattern, job_description.lower())
    if match:
        return int(match.group(1))
    return 0


def extract_required_education(job_description):
    text = job_description.lower()
    if any(k in text for k in ["bachelor", "b.tech", "btech", "b.e", "bca", "bsc", "b.sc"]):
        return "Bachelor's Degree"
    if any(k in text for k in ["master", "m.tech", "mtech", "mca", "mba", "msc", "m.sc"]):
        return "Master's Degree"
    return "Not Specified"


def check_education_match(candidate_education, required_education):
    if not required_education or required_education == "Not Specified":
        return 1

    candidate_edu_str = (
        " ".join(candidate_education).lower()
        if isinstance(candidate_education, list)
        else str(candidate_education).lower()
    )

    req_edu_lower = required_education.lower()

    bachelor_degrees = [
        "bachelor", "b.tech", "btech", "b.e", "be", "bca", "b.sc", "bsc", "b.com", "bcom"
    ]
    master_degrees = [
        "master", "m.tech", "mtech", "mca", "m.sc", "msc", "mba", "phd", "doctorate"
    ]

    has_bachelor = any(deg in candidate_edu_str for deg in bachelor_degrees)
    has_master = any(deg in candidate_edu_str for deg in master_degrees)

    if any(k in req_edu_lower for k in ["bachelor", "b.tech", "btech", "b.e", "bca"]):
        return 1 if (has_bachelor or has_master) else 0

    if any(k in req_edu_lower for k in ["master", "m.tech", "mca", "mba"]):
        return 1 if has_master else 0

    return 0


# =============================
# Manual TF-IDF & Cosine Similarity
# =============================

def calculate_tf(words):
    count = Counter(words)
    total = len(words)
    if total == 0:
        return {}
    return {word: value / total for word, value in count.items()}


def calculate_idf(documents):
    total = len(documents)
    frequency = Counter()
    for document in documents:
        for word in set(document):
            frequency[word] += 1
    return {
        word: math.log((total + 1) / (count + 1)) + 1
        for word, count in frequency.items()
    }


def calculate_tfidf(tf, idf):
    return {word: value * idf[word] for word, value in tf.items() if word in idf}


def cosine_similarity(v1, v2):
    common = set(v1) & set(v2)
    dot = sum(v1[word] * v2[word] for word in common)
    mag1 = math.sqrt(sum(value * value for value in v1.values()))
    mag2 = math.sqrt(sum(value * value for value in v2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


# =============================
# Core Scoring Algorithm
# =============================

def calculate_candidate_score(resume_text, job_description, preferred_skills=None):
    jd_skills = extract_jd_skills(job_description)
    required_experience = extract_required_experience(job_description)
    required_education = extract_required_education(job_description)

    profile = extract_candidate_profile(resume_text)
    candidate_skills = profile["skills"]
    experience = profile["experience"]
    education = profile["education"]

    matched_skills = [s for s in jd_skills if s in candidate_skills]
    missing_skills = [s for s in jd_skills if s not in candidate_skills]

    skill_score = (
        (len(matched_skills) / len(jd_skills)) * 100.0
        if len(jd_skills) > 0
        else 0.0
    )

    preferred_matched = []
    if preferred_skills:
        preferred_matched = [s for s in preferred_skills if s in candidate_skills]

    candidate_years = profile["experience_years"]
    experience_match = 1 if candidate_years >= required_experience else 0
    education_match = check_education_match(education, required_education)

    rule_score = (
        skill_score * 0.60
        + (experience_match * 20.0)
        + (education_match * 20.0)
    )

    resume_words = resume_text.lower().split()
    jd_words = job_description.lower().split()
    documents = [resume_words, jd_words]

    resume_tf = calculate_tf(resume_words)
    jd_tf = calculate_tf(jd_words)
    idf = calculate_idf(documents)

    resume_tfidf = calculate_tfidf(resume_tf, idf)
    jd_tfidf = calculate_tfidf(jd_tf, idf)
    similarity = cosine_similarity(resume_tfidf, jd_tfidf)
    tfidf_score = similarity * 100.0

    combined_score = (rule_score * 0.70) + (tfidf_score * 0.30)
    status = "Shortlisted" if combined_score >= 70.0 else "Review"

    return {
        "candidate_name": profile["name"],
        "candidate_email": profile["email"],
        "candidate_phone": profile["phone"],
        "candidate_skills": candidate_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "preferred_skills_matched": preferred_matched,
        "skill_score": round(skill_score, 2),
        "experience": experience,
        "required_experience": required_experience,
        "experience_match": "YES" if experience_match else "NO",
        "education": education,
        "required_education": required_education,
        "education_match": "YES" if education_match else "NO",
        "rule_based_score": round(rule_score, 2),
        "tfidf_similarity": round(similarity, 4),
        "tfidf_score": round(tfidf_score, 2),
        "combined_score": round(combined_score, 2),
        "status": status,
        "certifications": profile["certifications"],
        "projects": profile["projects"],
        "raw_text": resume_text
    }


# =============================
# API: Authentication
# =============================

@app.post("/api/auth/login")
def login(creds: LoginRequest):
    email = creds.email.strip().lower()
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not user or not verify_password(creds.password, user["password_hash"], user["salt"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials."
        )

    token = create_session(user["id"], user["email"])
    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"]
        }
    }


@app.post("/api/auth/logout")
def logout(request: Request):
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.headers.get("X-Session-Token")
    if token:
        delete_session(token)
    return {"message": "Logged out successfully"}


@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}


# =============================
# API: Dashboard Statistics
# =============================

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()

    total_candidates = cursor.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    total_screened = cursor.execute("SELECT COUNT(*) FROM screening_results").fetchone()[0]
    total_shortlisted = cursor.execute(
        "SELECT COUNT(*) FROM screening_results WHERE status = 'Shortlisted'"
    ).fetchone()[0]
    total_review = cursor.execute(
        "SELECT COUNT(*) FROM screening_results WHERE status = 'Review'"
    ).fetchone()[0]
    total_rejected = cursor.execute(
        "SELECT COUNT(*) FROM screening_results WHERE status = 'Not shortlisted'"
    ).fetchone()[0]
    total_jobs = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    # Score Distribution
    dist_80_100 = cursor.execute(
        "SELECT COUNT(*) FROM screening_results WHERE combined_score >= 80"
    ).fetchone()[0]
    dist_60_79 = cursor.execute(
        "SELECT COUNT(*) FROM screening_results WHERE combined_score >= 60 AND combined_score < 80"
    ).fetchone()[0]
    dist_40_59 = cursor.execute(
        "SELECT COUNT(*) FROM screening_results WHERE combined_score >= 40 AND combined_score < 60"
    ).fetchone()[0]
    dist_below_40 = cursor.execute(
        "SELECT COUNT(*) FROM screening_results WHERE combined_score < 40"
    ).fetchone()[0]

    # Recent Sessions
    recent_sessions_rows = cursor.execute(
        "SELECT * FROM screening_sessions ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    recent_sessions = [dict(row) for row in recent_sessions_rows]

    # Recent Top Candidates
    recent_candidates_rows = cursor.execute(
        """
        SELECT r.id, r.candidate_name, r.resume_filename, r.combined_score, r.status, r.created_at,
               j.title as job_title
        FROM screening_results r
        LEFT JOIN jobs j ON r.job_id = j.id
        ORDER BY r.created_at DESC, r.combined_score DESC LIMIT 5
        """
    ).fetchall()
    recent_candidates = [dict(row) for row in recent_candidates_rows]

    conn.close()

    return {
        "total_resumes_screened": total_screened,
        "total_unique_candidates": total_candidates,
        "total_shortlisted": total_shortlisted,
        "total_review": total_review,
        "total_rejected": total_rejected,
        "total_jobs": total_jobs,
        "score_distribution": {
            "80-100": dist_80_100,
            "60-79": dist_60_79,
            "40-59": dist_40_59,
            "<40": dist_below_40
        },
        "recent_sessions": recent_sessions,
        "recent_candidates": recent_candidates
    }


# =============================
# API: Job Management
# =============================

@app.get("/api/jobs")
def get_jobs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["required_skills"] = json.loads(d.get("required_skills") or "[]")
        except Exception:
            d["required_skills"] = []
        try:
            d["preferred_skills"] = json.loads(d.get("preferred_skills") or "[]")
        except Exception:
            d["preferred_skills"] = []
        result.append(d)
    return result


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job description not found")
    d = dict(row)
    d["required_skills"] = json.loads(d.get("required_skills") or "[]")
    d["preferred_skills"] = json.loads(d.get("preferred_skills") or "[]")
    return d


@app.post("/api/jobs")
def create_job(job: JobCreateRequest):
    req_skills = job.required_skills or extract_jd_skills(job.description)
    min_exp = job.min_experience if job.min_experience > 0 else extract_required_experience(job.description)
    edu = job.education if job.education and job.education != "Not Specified" else extract_required_education(job.description)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO jobs (title, description, required_skills, preferred_skills, min_experience, education)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            job.title.strip(),
            job.description.strip(),
            json.dumps(req_skills),
            json.dumps(job.preferred_skills or []),
            min_exp,
            edu
        )
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "message": "Job description created successfully",
        "job": {
            "id": job_id,
            "title": job.title,
            "description": job.description,
            "required_skills": req_skills,
            "preferred_skills": job.preferred_skills,
            "min_experience": min_exp,
            "education": edu
        }
    }


@app.put("/api/jobs/{job_id}")
def update_job(job_id: int, job: JobCreateRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE jobs
        SET title = ?, description = ?, required_skills = ?, preferred_skills = ?,
            min_experience = ?, education = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            job.title.strip(),
            job.description.strip(),
            json.dumps(job.required_skills or []),
            json.dumps(job.preferred_skills or []),
            job.min_experience,
            job.education,
            job_id
        )
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()

    if not updated:
        raise HTTPException(status_code=404, detail="Job description not found")

    return {"message": "Job description updated successfully"}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()

    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"message": "Job description deleted successfully"}


# =============================
# API: Single Resume Screening
# =============================

@app.post("/screen-resume")
async def screen_resume(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    job_id: Optional[int] = Form(None)
):
    temp_path = os.path.join(tempfile.gettempdir(), secrets.token_hex(8) + "_" + file.filename)
    contents = await file.read()

    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        resume_text = extract_resume_text(temp_path)
        if not resume_text:
            raise HTTPException(
                status_code=400,
                detail="Unable to extract text from the PDF. The file may be corrupt, empty, or scanned image-only."
            )

        jd_text = default_job_description
        job_record = None

        conn = get_db()
        if job_id:
            job_record = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if job_record:
                jd_text = job_record["description"]

        if job_description and job_description.strip():
            jd_text = job_description.strip()

        preferred_skills = []
        if job_record and job_record["preferred_skills"]:
            try:
                preferred_skills = json.loads(job_record["preferred_skills"])
            except Exception:
                preferred_skills = []

        result = calculate_candidate_score(resume_text, jd_text, preferred_skills=preferred_skills)
        result["resume"] = file.filename

        # Persist Candidate in SQLite
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO candidates (filename, name, email, phone, skills, experience, experience_years, education, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file.filename,
                result["candidate_name"],
                result["candidate_email"],
                result["candidate_phone"],
                json.dumps(result["candidate_skills"]),
                result["experience"],
                extract_experience_years(resume_text),
                json.dumps(result["education"]),
                resume_text
            )
        )
        candidate_id = cursor.lastrowid

        # Persist Screening Result
        cursor.execute(
            """
            INSERT INTO screening_results (
                candidate_id, job_id, resume_filename, candidate_name, candidate_email,
                skill_score, matched_skills, missing_skills, preferred_skills_matched,
                experience_match, education_match, tfidf_similarity, tfidf_score,
                rule_based_score, combined_score, rank, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                job_id,
                file.filename,
                result["candidate_name"],
                result["candidate_email"],
                result["skill_score"],
                json.dumps(result["matched_skills"]),
                json.dumps(result["missing_skills"]),
                json.dumps(result["preferred_skills_matched"]),
                result["experience_match"],
                result["education_match"],
                result["tfidf_similarity"],
                result["tfidf_score"],
                result["rule_based_score"],
                result["combined_score"],
                1,
                result["status"]
            )
        )
        conn.commit()
        conn.close()

        result["id"] = candidate_id
        return result

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# =============================
# API: Multiple Resume Screening
# =============================

@app.post("/screen-multiple-resumes")
async def screen_multiple_resumes(
    job_description: Optional[str] = Form(None),
    job_id: Optional[int] = Form(None),
    files: List[UploadFile] = File(...)
):
    conn = get_db()
    jd_text = ""
    job_title = "Ad-hoc Job Screening"
    preferred_skills = []

    if job_id:
        job_record = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if job_record:
            jd_text = job_record["description"]
            job_title = job_record["title"]
            try:
                preferred_skills = json.loads(job_record["preferred_skills"] or "[]")
            except Exception:
                preferred_skills = []

    if not jd_text:
        jd_text = (job_description or "").strip()

    if not jd_text:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="A job description is required. Please paste text or select a saved job."
        )

    candidates = []
    failed_files = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            failed_files.append({"filename": file.filename, "reason": "Only PDF files are supported."})
            continue

        temp_path = os.path.join(tempfile.gettempdir(), secrets.token_hex(8) + "_" + file.filename)
        contents = await file.read()

        with open(temp_path, "wb") as f:
            f.write(contents)

        try:
            resume_text = extract_resume_text(temp_path)
            if not resume_text:
                failed_files.append({
                    "filename": file.filename,
                    "reason": "File is empty, scanned without OCR, or text could not be extracted."
                })
                continue

            result = calculate_candidate_score(resume_text, jd_text, preferred_skills=preferred_skills)
            result["resume"] = file.filename
            candidates.append(result)

        except Exception as e:
            failed_files.append({"filename": file.filename, "reason": f"Processing error: {str(e)}"})

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # Sort descending by combined score
    candidates.sort(key=lambda c: c["combined_score"], reverse=True)

    # Assign ranks
    for index, candidate in enumerate(candidates, start=1):
        candidate["rank"] = index

    # Persist Session & Results in SQLite
    shortlisted_count = sum(1 for c in candidates if c["status"] == "Shortlisted")
    review_count = sum(1 for c in candidates if c["status"] == "Review")
    rejected_count = sum(1 for c in candidates if c["status"] == "Not shortlisted")

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO screening_sessions (job_id, job_title, total_candidates, shortlisted_count, review_count, rejected_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (job_id, job_title, len(candidates), shortlisted_count, review_count, rejected_count)
    )
    session_id = cursor.lastrowid

    for candidate in candidates:
        cursor.execute(
            """
            INSERT INTO candidates (filename, name, email, phone, skills, experience, experience_years, education, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate["resume"],
                candidate["candidate_name"],
                candidate["candidate_email"],
                candidate["candidate_phone"],
                json.dumps(candidate["candidate_skills"]),
                candidate["experience"],
                extract_experience_years(candidate["raw_text"]),
                json.dumps(candidate["education"]),
                candidate["raw_text"]
            )
        )
        cand_id = cursor.lastrowid
        candidate["id"] = cand_id

        cursor.execute(
            """
            INSERT INTO screening_results (
                session_id, candidate_id, job_id, resume_filename, candidate_name, candidate_email,
                skill_score, matched_skills, missing_skills, preferred_skills_matched,
                experience_match, education_match, tfidf_similarity, tfidf_score,
                rule_based_score, combined_score, rank, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                cand_id,
                job_id,
                candidate["resume"],
                candidate["candidate_name"],
                candidate["candidate_email"],
                candidate["skill_score"],
                json.dumps(candidate["matched_skills"]),
                json.dumps(candidate["missing_skills"]),
                json.dumps(candidate["preferred_skills_matched"]),
                candidate["experience_match"],
                candidate["education_match"],
                candidate["tfidf_similarity"],
                candidate["tfidf_score"],
                candidate["rule_based_score"],
                candidate["combined_score"],
                candidate["rank"],
                candidate["status"]
            )
        )

    conn.commit()
    conn.close()

    return {
        "job_title": job_title,
        "job_description": jd_text,
        "total_candidates": len(candidates),
        "candidates": candidates,
        "failed_files": failed_files
    }


# =============================
# API: Candidate Database & Search
# =============================

@app.get("/api/candidates")
def get_candidates(
    search: Optional[str] = None,
    status: Optional[str] = "all",
    job_id: Optional[int] = None,
    min_score: Optional[float] = 0.0,
    sort_by: Optional[str] = "score",
    limit: Optional[int] = 100
):
    conn = get_db()
    query = """
        SELECT r.id, r.candidate_id, r.resume_filename, r.candidate_name, r.candidate_email,
               r.skill_score, r.matched_skills, r.missing_skills, r.experience_match,
               r.education_match, r.tfidf_score, r.combined_score, r.status, r.rank,
               r.created_at, j.title as job_title, c.phone, c.skills as all_skills,
               c.experience, c.education
        FROM screening_results r
        LEFT JOIN jobs j ON r.job_id = j.id
        LEFT JOIN candidates c ON r.candidate_id = c.id
        WHERE 1=1
    """
    params = []

    if status and status.lower() != "all":
        query += " AND r.status = ?"
        params.append(status)

    if job_id:
        query += " AND r.job_id = ?"
        params.append(job_id)

    if min_score and min_score > 0:
        query += " AND r.combined_score >= ?"
        params.append(min_score)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query += " AND (LOWER(r.candidate_name) LIKE ? OR LOWER(r.candidate_email) LIKE ? OR LOWER(r.resume_filename) LIKE ? OR LOWER(c.skills) LIKE ?)"
        params.extend([term, term, term, term])

    if sort_by == "date":
        query += " ORDER BY r.created_at DESC"
    elif sort_by == "name":
        query += " ORDER BY r.candidate_name ASC"
    else:
        query += " ORDER BY r.combined_score DESC"

    query += f" LIMIT {int(limit)}"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    candidates = []
    for row in rows:
        d = dict(row)
        for key in ["matched_skills", "missing_skills", "all_skills", "education"]:
            try:
                d[key] = json.loads(d.get(key) or "[]")
            except Exception:
                d[key] = []
        candidates.append(d)

    return candidates


@app.get("/api/candidates/{candidate_id}")
def get_candidate_detail(candidate_id: int):
    conn = get_db()
    candidate = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    if not candidate:
        conn.close()
        raise HTTPException(status_code=404, detail="Candidate not found")

    screenings = conn.execute(
        """
        SELECT r.*, j.title as job_title
        FROM screening_results r
        LEFT JOIN jobs j ON r.job_id = j.id
        WHERE r.candidate_id = ?
        ORDER BY r.created_at DESC
        """,
        (candidate_id,)
    ).fetchall()
    conn.close()

    d = dict(candidate)
    d["skills"] = json.loads(d.get("skills") or "[]")
    d["education"] = json.loads(d.get("education") or "[]")
    d["screening_history"] = [dict(s) for s in screenings]
    return d


@app.patch("/api/candidates/{candidate_id}/status")
def update_candidate_status(candidate_id: int, body: StatusUpdateRequest):
    valid_statuses = ["Shortlisted", "Review", "Not shortlisted", "Rejected"]
    new_status = "Not shortlisted" if body.status in ["Rejected", "Not shortlisted"] else body.status
    if new_status not in ["Shortlisted", "Review", "Not shortlisted"]:
        raise HTTPException(status_code=400, detail="Invalid status category")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE screening_results SET status = ? WHERE id = ? OR candidate_id = ?",
        (new_status, candidate_id, candidate_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()

    if not updated:
        raise HTTPException(status_code=404, detail="Candidate record not found")

    return {"message": "Candidate status updated successfully", "status": new_status}


# =============================
# API: Skill-Based Search (ANY / ALL)
# =============================

@app.post("/api/candidates/skill-search")
def skill_search(body: SkillSearchRequest):
    search_skills = [s.strip().lower() for s in body.skills if s.strip()]
    if not search_skills:
        raise HTTPException(status_code=400, detail="At least one skill must be provided for searching.")

    conn = get_db()
    rows = conn.execute(
        """
        SELECT r.id, r.candidate_id, r.resume_filename, r.candidate_name, r.candidate_email,
               r.skill_score, r.combined_score, r.status, c.phone, c.skills as all_skills,
               c.experience, c.experience_years, c.education, j.title as job_title
        FROM screening_results r
        LEFT JOIN candidates c ON r.candidate_id = c.id
        LEFT JOIN jobs j ON r.job_id = j.id
        """
    ).fetchall()
    conn.close()

    matching_candidates = []

    for row in rows:
        d = dict(row)
        try:
            cand_skills = json.loads(d.get("all_skills") or "[]")
        except Exception:
            cand_skills = []

        cand_skills_lower = [s.lower() for s in cand_skills]
        matched = [s for s in search_skills if s in cand_skills_lower]
        missing = [s for s in search_skills if s not in cand_skills_lower]

        is_match = False
        if body.mode.upper() == "ALL":
            is_match = (len(matched) == len(search_skills))
        else:  # ANY
            is_match = (len(matched) > 0)

        if is_match:
            if body.min_score and (d.get("combined_score") or 0) < body.min_score:
                continue
            if body.status and body.status.lower() != "all" and d.get("status") != body.status:
                continue

            match_pct = round((len(matched) / len(search_skills)) * 100.0, 2)
            d["matched_search_skills"] = matched
            d["missing_search_skills"] = missing
            d["skill_match_percentage"] = match_pct
            matching_candidates.append(d)

    # Sort candidates by skill match percentage descending, then combined score
    matching_candidates.sort(
        key=lambda x: (x["skill_match_percentage"], x.get("combined_score") or 0),
        reverse=True
    )

    return {
        "searched_skills": search_skills,
        "mode": body.mode.upper(),
        "total_matched": len(matching_candidates),
        "candidates": matching_candidates
    }


# =============================
# API: CSV Export & Reports
# =============================

@app.get("/api/reports/export-csv")
def export_csv(
    status: Optional[str] = "all",
    job_id: Optional[int] = None,
    min_score: Optional[float] = 0.0
):
    conn = get_db()
    query = """
        SELECT r.rank, r.candidate_name, r.candidate_email, r.resume_filename,
               j.title as job_title, r.skill_score, r.experience_match, r.education_match,
               r.tfidf_score, r.combined_score, r.status, r.matched_skills, r.missing_skills
        FROM screening_results r
        LEFT JOIN jobs j ON r.job_id = j.id
        WHERE 1=1
    """
    params = []
    if status and status.lower() != "all":
        query += " AND r.status = ?"
        params.append(status)
    if job_id:
        query += " AND r.job_id = ?"
        params.append(job_id)
    if min_score and min_score > 0:
        query += " AND r.combined_score >= ?"
        params.append(min_score)

    query += " ORDER BY r.combined_score DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Rank", "Candidate Name", "Email", "Resume File", "Applied Job",
        "Skill Match %", "Experience Match", "Education Match",
        "TF-IDF Score", "Overall Score", "Status", "Matched Skills", "Missing Skills"
    ])

    for row in rows:
        d = dict(row)
        matched = ", ".join(json.loads(d.get("matched_skills") or "[]"))
        missing = ", ".join(json.loads(d.get("missing_skills") or "[]"))
        writer.writerow([
            d.get("rank") or "-",
            d.get("candidate_name") or "Not found",
            d.get("candidate_email") or "Not found",
            d.get("resume_filename") or "",
            d.get("job_title") or "General Screening",
            d.get("skill_score") or 0.0,
            d.get("experience_match") or "NO",
            d.get("education_match") or "NO",
            d.get("tfidf_score") or 0.0,
            d.get("combined_score") or 0.0,
            d.get("status") or "Review",
            matched,
            missing
        ])

    csv_data = output.getvalue()
    filename = f"candidates_shortlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# =============================
# Root Health
# =============================

@app.get("/")
def home():
    return {
        "system": "AI-Based Resume Screening and Candidate Shortlisting System",
        "status": "Online",
        "version": "2.0.0",
        "frontend_url": "http://127.0.0.1:8000/frontend/login.html"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)
