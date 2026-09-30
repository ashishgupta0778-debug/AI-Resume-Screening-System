import re
import math
from collections import Counter

from resume_extractor import (
    extract_resume_text,
    extract_skills,
    extract_experience,
    extract_education
)


# -----------------------------
# TF-IDF Functions
# -----------------------------

def calculate_tf(words):

    word_count = Counter(words)
    total_words = len(words)

    tf = {}

    for word, count in word_count.items():
        tf[word] = count / total_words

    return tf


def calculate_idf(documents):

    total_documents = len(documents)

    document_frequency = Counter()

    for document in documents:

        unique_words = set(document)

        for word in unique_words:
            document_frequency[word] += 1

    idf = {}

    for word, document_count in document_frequency.items():

        idf[word] = math.log(
            (total_documents + 1) /
            (document_count + 1)
        ) + 1

    return idf


def calculate_tfidf(tf, idf):

    tfidf = {}

    for word, tf_value in tf.items():

        if word in idf:
            tfidf[word] = tf_value * idf[word]

    return tfidf


def cosine_similarity(vector1, vector2):

    common_words = (
        set(vector1.keys()) &
        set(vector2.keys())
    )

    dot_product = 0

    for word in common_words:

        dot_product += (
            vector1[word] *
            vector2[word]
        )

    magnitude1 = math.sqrt(
        sum(
            value * value
            for value in vector1.values()
        )
    )

    magnitude2 = math.sqrt(
        sum(
            value * value
            for value in vector2.values()
        )
    )

    if magnitude1 == 0 or magnitude2 == 0:
        return 0

    return dot_product / (
        magnitude1 * magnitude2
    )


# -----------------------------
# 1. Read Job Description
# -----------------------------

with open("data/jobs/software_developer.txt", "r") as file:

    job_description = file.read()

job_description = job_description.lower()


# -----------------------------
# 2. Extract JD Requirements
# -----------------------------

required_skills = [
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

jd_skills = []

for skill in required_skills:

    if skill in job_description:
        jd_skills.append(skill)


# Required Experience

pattern = r"\b(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b"

match = re.search(
    pattern,
    job_description
)

if match:

    required_experience = int(
        match.group(1)
    )

else:

    required_experience = 0


# Required Education

if "bachelor's degree" in job_description:

    required_education = "bachelor"

else:

    required_education = ""


# -----------------------------
# 3. Extract PDF Resume Data
# -----------------------------

pdf_path = "data/resumes/sample_resume.pdf"

resume_text = extract_resume_text(
    pdf_path
)

candidate_skills = extract_skills(
    resume_text
)

candidate_experience = extract_experience(
    resume_text
)

candidate_education = extract_education(
    resume_text
)


# -----------------------------
# 4. Skill Matching
# -----------------------------

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


# -----------------------------
# 5. Experience Matching
# -----------------------------

if candidate_experience != "Not Mentioned":

    candidate_years = int(
        re.search(
            r"\d+",
            candidate_experience
        ).group()
    )

    if candidate_years >= required_experience:

        experience_match = 1

    else:

        experience_match = 0

else:

    experience_match = 0


# -----------------------------
# 6. Education Matching
# -----------------------------

candidate_education_text = str(
    candidate_education
).lower()

if "bachelor" in candidate_education_text:

    education_match = 1

else:

    education_match = 0


# -----------------------------
# 7. Final Score
# -----------------------------

final_score = (

    skill_score * 0.60

    + experience_match * 20

    + education_match * 20

)


# -----------------------------
# 8. TF-IDF Calculation
# -----------------------------

resume_words = resume_text.lower().split()

jd_words = job_description.split()

documents = [
    resume_words,
    jd_words
]

resume_tf = calculate_tf(
    resume_words
)

jd_tf = calculate_tf(
    jd_words
)

idf = calculate_idf(
    documents
)

resume_tfidf = calculate_tfidf(
    resume_tf,
    idf
)

jd_tfidf = calculate_tfidf(
    jd_tf,
    idf
)

tfidf_similarity = cosine_similarity(
    resume_tfidf,
    jd_tfidf
)

tfidf_score = tfidf_similarity * 100


# -----------------------------
# 9. Combined Score
# -----------------------------

combined_score = (

    final_score * 0.70

    + tfidf_score * 0.30

)


# -----------------------------
# 10. Display Result
# -----------------------------

print("\n================================")
print("PDF RESUME MATCHING RESULT")
print("================================")

print("\nCandidate Skills:")
print(candidate_skills)

print("\nRequired Skills:")
print(jd_skills)

print("\nMatched Skills:")
print(matched_skills)

print("\nSkill Score:")
print(round(skill_score, 2))

print("\nCandidate Experience:")
print(candidate_experience)

print("\nRequired Experience:")
print(required_experience, "years")

print("\nExperience Match:")
print(
    "YES"
    if experience_match == 1
    else "NO"
)

print("\nCandidate Education:")
print(candidate_education)

print("\nEducation Match:")
print(
    "YES"
    if education_match == 1
    else "NO"
)

print("\nRule-Based Final Score:")
print(round(final_score, 2))

print("\nTF-IDF Similarity:")
print(round(tfidf_similarity, 4))

print("\nTF-IDF Score:")
print(round(tfidf_score, 2))

print("\nCombined Score:")
print(round(combined_score, 2))