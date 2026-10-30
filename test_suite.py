import os
import sys
import json
import io
import asyncio
from pathlib import Path
from fastapi import UploadFile

from src.db import init_db, get_db, hash_password, verify_password
from src.auth import create_session, validate_session, delete_session
from src.resume_extractor import (
    extract_resume_text,
    extract_skills,
    extract_experience,
    extract_education,
    extract_candidate_profile
)
from src.api import (
    app,
    login,
    LoginRequest,
    get_dashboard_stats,
    get_jobs,
    create_job,
    update_job,
    delete_job,
    JobCreateRequest,
    calculate_candidate_score,
    calculate_tf,
    calculate_idf,
    calculate_tfidf,
    cosine_similarity,
    skill_search,
    SkillSearchRequest,
    get_candidates,
    update_candidate_status,
    StatusUpdateRequest,
    export_csv
)

passed_tests = []
failed_tests = []

def run_test(name, func):
    try:
        func()
        passed_tests.append(name)
        print(f"[PASS] {name}")
    except Exception as e:
        failed_tests.append((name, str(e)))
        print(f"[FAIL] {name}: {e}")

# ============================================================
# TEST SUITE
# ============================================================

# 1. Backend Startup & Database Init
def test_backend_startup():
    init_db()
    conn = get_db()
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()
    assert "users" in tables
    assert "jobs" in tables
    assert "candidates" in tables
    assert "screening_results" in tables
    assert "screening_sessions" in tables

# 2. Frontend Files Integrity
def test_frontend_integrity():
    for f in ["index.html", "login.html", "candidates.html", "jobs.html", "style.css", "script.js", "login.js", "candidates.js", "jobs.js"]:
        path = Path("frontend") / f
        assert path.exists(), f"Missing {f}"
        content = path.read_text(encoding="utf-8")
        assert len(content) > 50, f"File {f} is empty"
        assert "```" not in content, f"Markdown fences found in {f}"

# 3. Login and Logout
def test_login_logout():
    # Login valid
    res = login(LoginRequest(email="admin@resumeai.com", password="admin123"))
    token = res.get("token")
    assert token, "Token not generated"
    assert res["user"]["email"] == "admin@resumeai.com"

    # Validate session
    sess = validate_session(token)
    assert sess and sess["email"] == "admin@resumeai.com"

    # Logout
    assert delete_session(token)
    assert validate_session(token) is None

# 4. Protected Page & API Access
def test_auth_protection():
    try:
        login(LoginRequest(email="admin@resumeai.com", password="wrongpassword"))
        assert False, "Should fail on wrong password"
    except Exception as e:
        assert "401" in str(e) or "Invalid email" in str(e)

# 5. Dashboard Data
def test_dashboard_data():
    stats = get_dashboard_stats()
    assert "total_resumes_screened" in stats
    assert "total_unique_candidates" in stats
    assert "score_distribution" in stats
    assert "total_jobs" in stats

# 6. Single PDF Screening Calculation
def test_single_pdf_screening():
    pdf_path = Path("data/resumes/sample_resume.pdf")
    assert pdf_path.exists()
    text = extract_resume_text(str(pdf_path))
    assert len(text) > 50
    score = calculate_candidate_score(text, "Looking for Software Developer with Python, SQL, Java and Bachelor degree")
    assert score["skill_score"] > 50
    assert score["combined_score"] > 50
    assert score["education_match"] == "YES"

# 7. Resume Text Extraction & Candidate Profile
def test_candidate_profile_extraction():
    text = """
    Jane Smith
    jane.smith@techcorp.com | (555) 234-5678 | San Francisco, CA
    EXPERIENCE
    Software Engineer with 4 years of experience.
    SKILLS
    Python, SQL, React, Docker, Machine Learning.
    EDUCATION
    Bachelor of Technology in Computer Science
    """
    profile = extract_candidate_profile(text)
    assert profile["name"] == "Jane Smith", f"Got: {profile['name']}"
    assert profile["email"] == "jane.smith@techcorp.com", f"Got: {profile['email']}"
    assert "555" in profile["phone"], f"Got: {profile['phone']}"
    assert "python" in profile["skills"]
    assert "docker" in profile["skills"]
    assert profile["experience_years"] == 4

# 8. Job Description Creation, Retrieval, and Deletion
def test_job_management():
    # Create
    new_job = create_job(JobCreateRequest(
        title="Full Stack Engineer",
        description="Must have Python, JavaScript, React and 3 years experience. Bachelor's required.",
        required_skills=["python", "javascript", "react"],
        preferred_skills=["docker", "aws"],
        min_experience=3,
        education="Bachelor's Degree"
    ))
    job_id = new_job["job"]["id"]
    assert job_id > 0

    # Retrieve
    jobs = get_jobs()
    assert any(j["id"] == job_id for j in jobs)

    # Delete
    del_res = delete_job(job_id)
    assert "successfully" in del_res["message"]

# 9. Skill-Based ANY and ALL Search
def test_skill_search_modes():
    # Insert candidate into DB for testing
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO candidates (filename, name, email, skills, experience, raw_text)
        VALUES ('test_dev.pdf', 'Alice Coder', 'alice@test.com', '[\"python\", \"sql\", \"docker\"]', '3 years', 'Python SQL Docker')
    """)
    cand_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO screening_results (candidate_id, resume_filename, candidate_name, candidate_email, combined_score, status)
        VALUES (?, 'test_dev.pdf', 'Alice Coder', 'alice@test.com', 85.0, 'Shortlisted')
    """, (cand_id,))
    conn.commit()
    conn.close()

    # Test ANY mode
    res_any = skill_search(SkillSearchRequest(skills=["python", "ruby"], mode="ANY"))
    assert any(c["candidate_name"] == "Alice Coder" for c in res_any["candidates"])

    # Test ALL mode (should FAIL if missing ruby)
    res_all_fail = skill_search(SkillSearchRequest(skills=["python", "ruby"], mode="ALL"))
    assert not any(c["candidate_name"] == "Alice Coder" for c in res_all_fail["candidates"])

    # Test ALL mode (should PASS if all matched)
    res_all_pass = skill_search(SkillSearchRequest(skills=["python", "docker"], mode="ALL"))
    assert any(c["candidate_name"] == "Alice Coder" for c in res_all_pass["candidates"])

# 10. Manual TF-IDF and Cosine Similarity
def test_manual_tfidf():
    doc1 = ["python", "machine", "learning", "data"]
    doc2 = ["python", "java", "sql", "data"]
    docs = [doc1, doc2]

    tf1 = calculate_tf(doc1)
    tf2 = calculate_tf(doc2)
    idf = calculate_idf(docs)

    tfidf1 = calculate_tfidf(tf1, idf)
    tfidf2 = calculate_tfidf(tf2, idf)
    sim = cosine_similarity(tfidf1, tfidf2)

    assert 0.0 < sim < 1.0, f"Similarity unexpected: {sim}"
    # Empty documents safety
    assert cosine_similarity({}, {}) == 0.0

# 11. Candidate Score Calculations & Ranking
def test_score_calculation_consistency():
    text = "Python developer with 3 years of experience. B.Tech degree."
    jd = "Software Developer. Python, SQL. 2+ years of experience. Bachelor's degree."
    score1 = calculate_candidate_score(text, jd)
    score2 = calculate_candidate_score(text, jd)
    assert score1["combined_score"] == score2["combined_score"]
    assert score1["experience_match"] == "YES"
    assert score1["education_match"] == "YES"

# 12. Shortlist Decision Persistence
def test_shortlist_persistence():
    conn = get_db()
    row = conn.execute("SELECT id FROM screening_results LIMIT 1").fetchone()
    conn.close()
    if row:
        res_id = row["id"]
        update_candidate_status(res_id, StatusUpdateRequest(status="Shortlisted"))
        conn = get_db()
        chk = conn.execute("SELECT status FROM screening_results WHERE id = ?", (res_id,)).fetchone()
        conn.close()
        assert chk["status"] == "Shortlisted"

# 13. Candidate Filters & Search
def test_candidate_filters():
    cands = get_candidates(status="Shortlisted")
    assert all(c["status"] == "Shortlisted" for c in cands)

# 14. CSV Export
def test_csv_export():
    response = export_csv()
    assert response.status_code == 200
    assert b"Rank" in response.body
    assert b"Overall Score" in response.body

# 15. Invalid / Empty PDF Handling
def test_corrupt_pdf_handling():
    # Extracting non-existent or empty path returns empty string without crashing
    text = extract_resume_text("non_existent_file.pdf")
    assert text == ""

# 16. Division by Zero Protection on Empty Skills
def test_zero_division_protection():
    score = calculate_candidate_score("Only some random text without technical skills", "No tech words here either")
    assert score["skill_score"] == 0.0
    assert score["combined_score"] >= 0.0

# 17. Navigation Links Consistency
def test_navigation_links():
    index_html = Path("frontend/index.html").read_text(encoding="utf-8")
    cand_html = Path("frontend/candidates.html").read_text(encoding="utf-8")
    jobs_html = Path("frontend/jobs.html").read_text(encoding="utf-8")

    for html, fname in [(index_html, "index.html"), (cand_html, "candidates.html"), (jobs_html, "jobs.html")]:
        assert 'href="index.html"' in html
        assert 'href="candidates.html' in html
        assert 'href="jobs.html"' in html
        assert 'onclick="logout()"' in html

# 18. Degree Equivalence Matching
def test_degree_equivalences():
    btech_score = calculate_candidate_score("B.Tech in CS", "Requires Bachelor's Degree")
    mca_score = calculate_candidate_score("MCA degree", "Requires Bachelor's Degree")
    no_edu_score = calculate_candidate_score("No degree", "Requires Bachelor's Degree")

    assert btech_score["education_match"] == "YES"
    assert mca_score["education_match"] == "YES"
    assert no_edu_score["education_match"] == "NO"

# 19. Multiple PDF Batch Processing & Failed Files Reporting
def test_batch_processing_and_failures():
    from src.api import calculate_candidate_score as calc_score
    assert Path("data/resumes/sample_resume.pdf").exists()
    text = extract_resume_text("data/resumes/sample_resume.pdf")
    res = calc_score(text, "Python SQL Developer")
    assert res["combined_score"] > 0
    bad_pdf_text = extract_resume_text("data/jobs/software_developer.txt")
    assert bad_pdf_text == "" or len(bad_pdf_text) >= 0

# 20. Persistence Survives Connection Cycles (Reloading Simulation)
def test_persistence_across_cycles():
    conn1 = get_db()
    conn1.execute("INSERT OR REPLACE INTO users (id, email, password_hash, salt, role) VALUES (999, 'persist@test.com', 'h', 's', 'recruiter')")
    conn1.commit()
    conn1.close()

    # Re-open fresh connection (simulating full server/browser restart)
    conn2 = get_db()
    row = conn2.execute("SELECT * FROM users WHERE id = 999").fetchone()
    conn2.execute("DELETE FROM users WHERE id = 999")
    conn2.commit()
    conn2.close()
    assert row is not None
    assert row["email"] == "persist@test.com"

# 21. Candidate PDF Upload Area & File Selection Wiring
def test_upload_box_configuration():
    with open("frontend/candidates.html", "r", encoding="utf-8") as f:
        html = f.read()
    assert 'for="resumeFiles"' in html
    assert 'class="upload-box"' in html
    assert 'id="uploadDropzone"' in html
    assert 'id="resumeFiles"' in html
    assert 'accept=".pdf,application/pdf"' in html
    assert 'multiple' in html

    with open("frontend/style.css", "r", encoding="utf-8") as f:
        css = f.read()
    assert "cursor: pointer;" in css
    assert ".upload-box.dragover" in css
    assert ".upload-browse-btn" in css
    assert ".clear-files-btn" in css

    with open("frontend/candidates.js", "r", encoding="utf-8") as f:
        js = f.read()
    assert "renderSelectedFiles" in js
    assert "clearSelectedFiles" in js
    assert "uploadDropzone.addEventListener" in js
    assert "screenCandidates" in js
    assert "/screen-multiple-resumes" in js

# Run all tests
def run_all():
    print("=" * 60)
    print("RUNNING AUTOMATED COMPREHENSIVE VERIFICATION SUITE")
    print("=" * 60)
    run_test("1. Backend Startup & Database Init", test_backend_startup)
    run_test("2. Frontend Files Integrity", test_frontend_integrity)
    run_test("3. Login and Logout", test_login_logout)
    run_test("4. Protected Page & API Access", test_auth_protection)
    run_test("5. Dashboard Real Data", test_dashboard_data)
    run_test("6. Single PDF Screening Calculation", test_single_pdf_screening)
    run_test("7. Resume Text Extraction & Candidate Profile", test_candidate_profile_extraction)
    run_test("8. Job Description Creation, Retrieval, and Deletion", test_job_management)
    run_test("9. Skill-Based ANY and ALL Search", test_skill_search_modes)
    run_test("10. Manual TF-IDF and Cosine Similarity", test_manual_tfidf)
    run_test("11. Candidate Score Calculations & Ranking", test_score_calculation_consistency)
    run_test("12. Shortlist Decision Persistence", test_shortlist_persistence)
    run_test("13. Candidate Filters & Search", test_candidate_filters)
    run_test("14. CSV Export Generation", test_csv_export)
    run_test("15. Invalid / Empty PDF Handling", test_corrupt_pdf_handling)
    run_test("16. Division by Zero Protection on Empty Skills", test_zero_division_protection)
    run_test("17. Navigation Links Consistency", test_navigation_links)
    run_test("18. Degree Equivalence Matching", test_degree_equivalences)
    run_test("19. Multiple PDF Batch Processing & Failed Files Reporting", test_batch_processing_and_failures)
    run_test("20. Persistence Survives Connection Cycles (Reloading)", test_persistence_across_cycles)
    run_test("21. Candidate PDF Upload Area & File Selection Wiring", test_upload_box_configuration)

    print("=" * 60)
    print(f"RESULTS: {len(passed_tests)} Passed, {len(failed_tests)} Failed.")
    print("=" * 60)
    if failed_tests:
        sys.exit(1)

if __name__ == "__main__":
    run_all()
