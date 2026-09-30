import os
import re
import math
import pandas as pd
from collections import Counter

from resume_extractor import (
    extract_resume_text,
    extract_skills,
    extract_experience,
    extract_education
)


# =============================
# 1. READ JOB DESCRIPTION
# =============================

with open("data/jobs/software_developer.txt", "r") as file:
    job_description = file.read().lower()


# =============================
# 2. JD REQUIREMENTS
# =============================

required_skills = [
    "python", "java", "c++", "c#", "sql",
    "html", "css", "javascript", "react",
    "machine learning", "communication",
    "problem solving", "database management", "apis"
]

jd_skills = []

for skill in required_skills:
    if skill in job_description:
        jd_skills.append(skill)


pattern = r"\b(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b"

match = re.search(pattern, job_description)

if match:
    required_experience = int(match.group(1))
else:
    required_experience = 0


required_education = "bachelor" if "bachelor's degree" in job_description else ""


# =============================
# 3. TF-IDF FUNCTIONS
# =============================

def calculate_tf(words):

    count = Counter(words)
    total = len(words)

    return {
        word: value / total
        for word, value in count.items()
    }


def calculate_idf(documents):

    total_documents = len(documents)
    frequency = Counter()

    for document in documents:
        for word in set(document):
            frequency[word] += 1

    return {
        word: math.log(
            (total_documents + 1) /
            (count + 1)
        ) + 1
        for word, count in frequency.items()
    }


def calculate_tfidf(tf, idf):

    return {
        word: tf_value * idf[word]
        for word, tf_value in tf.items()
        if word in idf
    }


def cosine_similarity(vector1, vector2):

    common = set(vector1) & set(vector2)

    dot = sum(
        vector1[word] * vector2[word]
        for word in common
    )

    magnitude1 = math.sqrt(
        sum(value * value for value in vector1.values())
    )

    magnitude2 = math.sqrt(
        sum(value * value for value in vector2.values())
    )

    if magnitude1 == 0 or magnitude2 == 0:
        return 0

    return dot / (magnitude1 * magnitude2)


# =============================
# 4. FIND ALL PDF RESUMES
# =============================

resume_folder = "data/resumes"

pdf_files = [
    file for file in os.listdir(resume_folder)
    if file.lower().endswith(".pdf")
]

print("\n================================")
print("AI RESUME SCREENING SYSTEM")
print("================================")

print("\nTotal PDF Resumes:", len(pdf_files))


# =============================
# 5. PROCESS EVERY PDF
# =============================

results = []

for pdf_file in pdf_files:

    print("\nProcessing:", pdf_file)

    pdf_path = os.path.join(
        resume_folder,
        pdf_file
    )

    resume_text = extract_resume_text(pdf_path)

    candidate_skills = extract_skills(resume_text)

    candidate_experience = extract_experience(resume_text)

    candidate_education = extract_education(resume_text)


    # -------------------------
    # Skill Matching
    # -------------------------

    matched_skills = []

    for skill in jd_skills:

        if skill in candidate_skills:
            matched_skills.append(skill)


    if len(jd_skills) > 0:

        skill_score = (
            len(matched_skills) /
            len(jd_skills)
        ) * 100

    else:

        skill_score = 0


    # -------------------------
    # Experience Matching
    # -------------------------

    if candidate_experience != "Not Mentioned":

        candidate_years = int(
            re.search(
                r"\d+",
                candidate_experience
            ).group()
        )

        experience_match = (
            1
            if candidate_years >= required_experience
            else 0
        )

    else:

        experience_match = 0


    # -------------------------
    # Education Matching
    # -------------------------

    education_text = str(
        candidate_education
    ).lower()

    education_match = (
        1
        if "bachelor" in education_text
        else 0
    )


    # -------------------------
    # Rule-Based Score
    # -------------------------

    final_score = (
        skill_score * 0.60
        + experience_match * 20
        + education_match * 20
    )


    # -------------------------
    # TF-IDF
    # -------------------------

    resume_words = resume_text.lower().split()

    jd_words = job_description.split()

    documents = [
        resume_words,
        jd_words
    ]

    resume_tf = calculate_tf(resume_words)

    jd_tf = calculate_tf(jd_words)

    idf = calculate_idf(documents)

    resume_tfidf = calculate_tfidf(
        resume_tf,
        idf
    )

    jd_tfidf = calculate_tfidf(
        jd_tf,
        idf
    )

    similarity = cosine_similarity(
        resume_tfidf,
        jd_tfidf
    )

    tfidf_score = similarity * 100


    # -------------------------
    # Combined Score
    # -------------------------

    combined_score = (
        final_score * 0.70
        + tfidf_score * 0.30
    )


    # -------------------------
    # Store Result
    # -------------------------

    results.append({

        "Resume": pdf_file,

        "Matched_Skills":
            ", ".join(matched_skills),

        "Skill_Score":
            round(skill_score, 2),

        "Experience_Match":
            experience_match,

        "Education_Match":
            education_match,

        "Rule_Based_Score":
            round(final_score, 2),

        "TFIDF_Score":
            round(tfidf_score, 2),

        "Combined_Score":
            round(combined_score, 2)
    })


# =============================
# 6. CREATE RANKING
# =============================

result_df = pd.DataFrame(results)

result_df = result_df.sort_values(
    by="Combined_Score",
    ascending=False
)

result_df.insert(
    0,
    "Rank",
    range(1, len(result_df) + 1)
)


# =============================
# 7. DISPLAY TOP CANDIDATES
# =============================

print("\n================================")
print("FINAL CANDIDATE RANKING")
print("================================")

print(
    result_df.head(10).to_string(
        index=False
    )
)


# =============================
# 8. SAVE RESULT
# =============================

os.makedirs(
    "data/results",
    exist_ok=True
)

result_df.to_csv(
    "data/results/pdf_candidate_ranking.csv",
    index=False
)

print("\n================================")
print("SUCCESS")
print("================================")

print(
    "\nRanking saved to:"
)

print(
    "data/results/pdf_candidate_ranking.csv"
)