import pymupdf as fitz
import re


def extract_resume_text(pdf_path):
    """
    Extract text safely from a PDF file.
    Handles corrupt, empty, scanned, or unreadable PDFs gracefully.
    """
    try:
        document = fitz.open(pdf_path)
        text = ""
        for page in document:
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
        document.close()
        return text.strip()
    except Exception as e:
        return ""


# -----------------------------
# Skills Catalog
# -----------------------------

TECHNICAL_SKILLS = [
    "python",
    "java",
    "c++",
    "c#",
    "sql",
    "html",
    "css",
    "javascript",
    "react",
    "node.js",
    "machine learning",
    "deep learning",
    "data analysis",
    "database management",
    "database",
    "databases",
    "apis",
    "git",
    "github",
    "mongodb",
    "mysql",
    "postgresql",
    "excel",
    "power bi",
    "aws",
    "docker",
    "kubernetes",
    "linux",
    "cloud computing"
]

SOFT_SKILLS = [
    "communication",
    "problem solving",
    "teamwork",
    "team work",
    "leadership",
    "adaptability",
    "critical thinking",
    "collaboration",
    "time management"
]

SKILLS_CATALOG = TECHNICAL_SKILLS + SOFT_SKILLS


# -----------------------------
# Extract Skills
# -----------------------------

def extract_skills(text, custom_skills=None):
    skills_to_check = custom_skills if custom_skills is not None else SKILLS_CATALOG
    text_lower = text.lower()
    found_skills = []

    for skill in skills_to_check:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return found_skills


# -----------------------------
# Extract Experience
# -----------------------------

def extract_experience(text):
    pattern = r"\b(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b"
    match = re.search(pattern, text.lower())

    if match:
        return match.group(1) + " years"

    # Secondary pattern: e.g. "Experience: 3 years"
    sec_pattern = r"experience\s*[:\-]\s*(\d+)\+?\s*(?:years?|yrs?)"
    sec_match = re.search(sec_pattern, text.lower())
    if sec_match:
        return sec_match.group(1) + " years"

    return "Not Mentioned"


def extract_experience_years(text):
    exp_str = extract_experience(text)
    if exp_str != "Not Mentioned":
        match = re.search(r"\d+", exp_str)
        if match:
            return int(match.group())
    return 0


# -----------------------------
# Extract Education
# -----------------------------

def extract_education(text):
    education_keywords = [
        "b.tech",
        "btech",
        "b.e",
        "be",
        "bca",
        "b.sc",
        "bsc",
        "b.com",
        "bcom",
        "bachelor's degree",
        "bachelor degree",
        "m.tech",
        "mtech",
        "mca",
        "m.sc",
        "msc",
        "mba",
        "master's degree",
        "master degree",
        "phd",
        "doctorate"
    ]

    text_lower = text.lower()
    found_education = []

    for education in education_keywords:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(education) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text_lower):
            found_education.append(education)

    if found_education:
        return found_education

    return ["Not Mentioned"]


# -----------------------------
# Extract Candidate Name
# -----------------------------

def extract_name(text):
    if not text:
        return "Not found"

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    ignore_words = {
        "resume", "curriculum", "vitae", "summary", "objective", "profile",
        "contact", "experience", "education", "skills", "projects", "developer",
        "engineer", "analyst", "manager", "phone", "email", "address"
    }

    # Inspect top 6 non-empty lines
    for line in lines[:6]:
        cleaned = re.sub(r"[^a-zA-Z\s]", " ", line).strip()
        words = cleaned.split()
        if 2 <= len(words) <= 4:
            if not any(w.lower() in ignore_words for w in words):
                return " ".join(w.capitalize() for w in words)

    return "Not found"


# -----------------------------
# Extract Email
# -----------------------------

def extract_email(text):
    if not text:
        return "Not found"
    match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", text)
    return match.group(0).lower() if match else "Not found"


# -----------------------------
# Extract Phone
# -----------------------------

def extract_phone(text):
    if not text:
        return "Not found"
    match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3,5}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b", text)
    return match.group(0).strip() if match else "Not found"


# -----------------------------
# Extract Certifications
# -----------------------------

def extract_certifications(text):
    if not text:
        return []

    cert_catalog = [
        "aws certified", "azure certified", "gcp certified", "pmp",
        "scrum master", "cisco", "ccna", "comptia", "certified kubernetes",
        "oracle certified", "istqb"
    ]
    text_lower = text.lower()
    found = []
    for cert in cert_catalog:
        if cert in text_lower:
            found.append(cert.title())
    return found


# -----------------------------
# Extract Projects
# -----------------------------

def extract_projects(text):
    if not text:
        return []

    lines = text.split("\n")
    in_project_section = False
    projects = []

    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        if re.search(r"\b(projects|academic projects|key projects)\b", cleaned.lower()):
            in_project_section = True
            continue
        if in_project_section:
            if re.search(r"\b(education|experience|skills|certifications|awards|summary|declaration)\b", cleaned.lower()):
                in_project_section = False
                break
            if len(cleaned) > 10 and not cleaned.startswith(("http", "www")):
                projects.append(cleaned[:100])
                if len(projects) >= 4:
                    break

    return projects


# -----------------------------
# Comprehensive Candidate Profile
# -----------------------------

def extract_candidate_profile(text, filename="Resume"):
    return {
        "filename": filename,
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "experience": extract_experience(text),
        "experience_years": extract_experience_years(text),
        "education": extract_education(text),
        "certifications": extract_certifications(text),
        "projects": extract_projects(text),
        "raw_text": text
    }


# -----------------------------
# Main Test
# -----------------------------

if __name__ == "__main__":
    pdf_path = "data/resumes/sample_resume.pdf"
    resume_text = extract_resume_text(pdf_path)
    profile = extract_candidate_profile(resume_text, "sample_resume.pdf")

    print("\n--- Extracted Profile ---")
    print("Name:", profile["name"])
    print("Email:", profile["email"])
    print("Phone:", profile["phone"])
    print("Skills:", profile["skills"])
    print("Experience:", profile["experience"])
    print("Education:", profile["education"])
