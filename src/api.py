from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

import os
import re
import math
import tempfile
from collections import Counter

from src.resume_extractor import (
    extract_resume_text,
    extract_skills,
    extract_experience,
    extract_education
)


# =============================
# FASTAPI APP
# =============================

app = FastAPI(
    title="AI Resume Screening System"
)


# =============================
# CORS
# =============================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================
# JOB DESCRIPTION
# =============================

with open(
    "data/jobs/software_developer.txt",
    "r"
) as file:

    job_description = file.read().lower()


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


jd_skills = [
    skill
    for skill in required_skills
    if skill in job_description
]


# =============================
# REQUIRED EXPERIENCE
# =============================

pattern = r"\b(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b"

match = re.search(
    pattern,
    job_description
)


required_experience = (
    int(match.group(1))
    if match
    else 0
)


# =============================
# TF-IDF
# =============================

def calculate_tf(words):

    count = Counter(words)

    total = len(words)

    if total == 0:
        return {}

    return {
        word: value / total
        for word, value in count.items()
    }


def calculate_idf(documents):

    total = len(documents)

    frequency = Counter()

    for document in documents:

        for word in set(document):

            frequency[word] += 1


    return {
        word: math.log(
            (total + 1) / (count + 1)
        ) + 1

        for word, count in frequency.items()
    }


def calculate_tfidf(tf, idf):

    return {
        word: value * idf[word]

        for word, value in tf.items()

        if word in idf
    }


def cosine_similarity(v1, v2):

    common = set(v1) & set(v2)

    dot = sum(
        v1[word] * v2[word]
        for word in common
    )


    mag1 = math.sqrt(
        sum(
            value * value
            for value in v1.values()
        )
    )


    mag2 = math.sqrt(
        sum(
            value * value
            for value in v2.values()
        )
    )


    if mag1 == 0 or mag2 == 0:

        return 0


    return dot / (mag1 * mag2)


# =============================
# HOME API
# =============================

@app.get("/")
def home():

    return {
        "message": "AI Resume Screening API is running"
    }


# =============================
# SCREEN RESUME API
# =============================

@app.post("/screen-resume")
async def screen_resume(
    file: UploadFile = File(...)
):

    # =============================
    # SAVE TEMPORARY PDF
    # =============================

    temp_path = os.path.join(
        tempfile.gettempdir(),
        file.filename
    )


    contents = await file.read()


    with open(
        temp_path,
        "wb"
    ) as f:

        f.write(contents)


    # =============================
    # EXTRACT RESUME INFORMATION
    # =============================

    resume_text = extract_resume_text(
        temp_path
    )


    skills = extract_skills(
        resume_text
    )


    experience = extract_experience(
        resume_text
    )


    education = extract_education(
        resume_text
    )


    # =============================
    # SKILL MATCHING
    # =============================

    matched_skills = [

        skill

        for skill in jd_skills

        if skill in skills

    ]


    skill_score = (

        len(matched_skills)
        /
        len(jd_skills)
        * 100

        if jd_skills

        else 0

    )


    # =============================
    # EXPERIENCE MATCHING
    # =============================

    if experience != "Not Mentioned":

        years = int(

            re.search(
                r"\d+",
                experience
            ).group()

        )


        experience_match = (

            1

            if years >= required_experience

            else 0

        )

    else:

        experience_match = 0


    # =============================
    # EDUCATION MATCHING
    # =============================

    education_match = (

        1

        if "bachelor"
        in str(education).lower()

        else 0

    )


    # =============================
    # RULE BASED SCORE
    # =============================

    rule_score = (

        skill_score * 0.60

        + experience_match * 20

        + education_match * 20

    )


    # =============================
    # TF-IDF
    # =============================

    resume_words = (
        resume_text.lower().split()
    )


    jd_words = (
        job_description.split()
    )


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


    similarity = cosine_similarity(

        resume_tfidf,
        jd_tfidf

    )


    tfidf_score = (
        similarity * 100
    )


    # =============================
    # COMBINED SCORE
    # =============================

    combined_score = (

        rule_score * 0.70

        + tfidf_score * 0.30

    )


    # =============================
    # REMOVE TEMPORARY FILE
    # =============================

    os.remove(temp_path)


    # =============================
    # RETURN RESULT
    # =============================

    return {

        "resume":
            file.filename,

        "candidate_skills":
            skills,

        "matched_skills":
            matched_skills,

        "skill_score":
            round(
                skill_score,
                2
            ),

        "experience":
            experience,

        "experience_match":

            "YES"

            if experience_match

            else "NO",

        "education":
            education,

        "education_match":

            "YES"

            if education_match

            else "NO",

        "rule_based_score":
            round(
                rule_score,
                2
            ),

        "tfidf_score":
            round(
                tfidf_score,
                2
            ),

        "combined_score":
            round(
                combined_score,
                2
            )

    }