import fitz
import re


def extract_resume_text(pdf_path):

    document = fitz.open(pdf_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text


# -----------------------------
# Extract Skills
# -----------------------------

def extract_skills(text):

    skills_list = [
        "python",
        "java",
        "c++",
        "c#",
        "sql",
        "html",
        "css",
        "javascript",
        "react",
        "machine learning",
        "communication",
        "problem solving",
        "database management",
        "apis"
    ]

    text_lower = text.lower()

    found_skills = []

    for skill in skills_list:

        if skill in text_lower:
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

    return "Not Mentioned"


# -----------------------------
# Extract Education
# -----------------------------

def extract_education(text):

    education_keywords = [
        "b.tech",
        "btech",
        "b.e",
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

        if education in text_lower:
            found_education.append(education)

    if found_education:
        return found_education

    return ["Not Mentioned"]


# -----------------------------
# Main Program
# -----------------------------

if __name__ == "__main__":

    pdf_path = "data/resumes/sample_resume.pdf"

    resume_text = extract_resume_text(pdf_path)

    print("\nResume Text:")
    print(resume_text[:2000])

    skills = extract_skills(resume_text)

    experience = extract_experience(resume_text)

    education = extract_education(resume_text)

    print("\n-----------------------------")

    print("\nExtracted Skills:")
    print(skills)

    print("\nExtracted Experience:")
    print(experience)

    print("\nExtracted Education:")
    print(education)