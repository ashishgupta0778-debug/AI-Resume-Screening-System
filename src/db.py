import sqlite3
import os
import json
import hashlib
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "resume_ai.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    salt_bytes = bytes.fromhex(salt)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 100000)
    return key.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    expected_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(expected_hash, password_hash)


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # Jobs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        required_skills TEXT DEFAULT '[]',
        preferred_skills TEXT DEFAULT '[]',
        min_experience INTEGER DEFAULT 0,
        education TEXT DEFAULT 'Not Specified',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Candidates Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        name TEXT DEFAULT 'Not found',
        email TEXT DEFAULT 'Not found',
        phone TEXT DEFAULT 'Not found',
        skills TEXT DEFAULT '[]',
        experience TEXT DEFAULT 'Not Mentioned',
        experience_years INTEGER DEFAULT 0,
        education TEXT DEFAULT '[]',
        raw_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Screening Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS screening_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        job_title TEXT,
        total_candidates INTEGER DEFAULT 0,
        shortlisted_count INTEGER DEFAULT 0,
        review_count INTEGER DEFAULT 0,
        rejected_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Screening Results Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS screening_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        candidate_id INTEGER,
        job_id INTEGER,
        resume_filename TEXT,
        candidate_name TEXT,
        candidate_email TEXT,
        skill_score REAL DEFAULT 0.0,
        matched_skills TEXT DEFAULT '[]',
        missing_skills TEXT DEFAULT '[]',
        preferred_skills_matched TEXT DEFAULT '[]',
        experience_match TEXT DEFAULT 'NO',
        education_match TEXT DEFAULT 'NO',
        tfidf_similarity REAL DEFAULT 0.0,
        tfidf_score REAL DEFAULT 0.0,
        rule_based_score REAL DEFAULT 0.0,
        combined_score REAL DEFAULT 0.0,
        rank INTEGER DEFAULT 1,
        status TEXT DEFAULT 'Review',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES screening_sessions (id),
        FOREIGN KEY (candidate_id) REFERENCES candidates (id)
    );
    """)

    # Seed Admin Users if none exists
    for admin_email in ["admin@resumeai.com", "admin@hcl.com"]:
        cursor.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
        if not cursor.fetchone():
            pwd_hash, salt = hash_password("admin123")
            cursor.execute(
                "INSERT INTO users (email, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                (admin_email, pwd_hash, salt, "admin")
            )

    # Seed Default Job if jobs table is empty
    cursor.execute("SELECT id FROM jobs LIMIT 1")
    if not cursor.fetchone():
        default_jd_file = BASE_DIR / "data" / "jobs" / "software_developer.txt"
        default_desc = ""
        if default_jd_file.exists():
            with open(default_jd_file, "r", encoding="utf-8") as f:
                default_desc = f.read()
        else:
            default_desc = "Software Developer role requiring Python, Java, SQL, and 2+ years experience."

        cursor.execute(
            """
            INSERT INTO jobs (title, description, required_skills, preferred_skills, min_experience, education)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Software Developer",
                default_desc,
                json.dumps(["python", "java", "sql", "html", "css", "javascript", "apis"]),
                json.dumps(["machine learning", "docker", "aws"]),
                2,
                "Bachelor's Degree"
            )
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
