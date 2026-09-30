import pandas as pd
import ast
import re


# --------------------------------------------------
# 1. Read Job Description
# --------------------------------------------------

with open("data/jobs/software_developer.txt", "r") as file:
    job_description = file.read()

print("JOB DESCRIPTION:")
print(job_description)


# --------------------------------------------------
# 2. Skills list
# --------------------------------------------------

skills = [
    "python",
    "java",
    "c++",
    "c#",
    "sql",
    "machine learning",
    "data analysis",
    "excel",
    "html",
    "css",
    "javascript",
    "react",
    "communication",
    "marketing",
    "accounting",
    "apis",
    "databases"
]


# --------------------------------------------------
# 3. Convert JD to lowercase
# --------------------------------------------------

jd_text = job_description.lower()


# --------------------------------------------------
# 4. Find required skills
# --------------------------------------------------

required_skills = []

for skill in skills:

    if skill in jd_text:
        required_skills.append(skill)


print("\nRequired Skills:")
print(required_skills)


# --------------------------------------------------
# 5. Extract required experience
# --------------------------------------------------

experience_pattern = r"\b(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b"

match = re.search(
    experience_pattern,
    jd_text
)

if match:
    required_experience = match.group(1)
else:
    required_experience = "Not Mentioned"


print("\nRequired Experience:")
print(required_experience, "years")


# --------------------------------------------------
# 6. Education keywords
# --------------------------------------------------

education_keywords = [
    "bachelor's degree",
    "bachelor degree",
    "master's degree",
    "master degree",
    "phd",
    "doctorate"
]


# --------------------------------------------------
# 7. Find required education
# --------------------------------------------------

required_education = []

for education in education_keywords:

    if education in jd_text:
        required_education.append(education)


if required_education:

    print("\nRequired Education:")
    print(required_education)

else:

    print("\nRequired Education:")
    print("Not Mentioned")


# --------------------------------------------------
# 8. Store Job Description requirements
# --------------------------------------------------

job_requirements = {
    "skills": required_skills,
    "experience": required_experience,
    "education": required_education
}


print("\nJob Requirements:")
print(job_requirements)


# --------------------------------------------------
# 9. Load cleaned resume dataset
# --------------------------------------------------

resume_df = pd.read_csv(
    "data/resume/cleaned_resume.csv"
)


# --------------------------------------------------
# 10. Match skills for all candidates
# --------------------------------------------------

results = []

for i in range(len(resume_df)):

    candidate_skills = ast.literal_eval(
        resume_df["Skills"].iloc[i]
    )

    matched_skills = []

    for skill in job_requirements["skills"]:

        if skill in candidate_skills:
            matched_skills.append(skill)


    results.append({

        # Candidate ID added
        "ID": resume_df["ID"].iloc[i],

        "Category": resume_df["Category"].iloc[i],

        "Skills": candidate_skills,

        "Matched_Skills": matched_skills,

        "Match_Count": len(matched_skills)

    })


# --------------------------------------------------
# 11. Convert results into DataFrame
# --------------------------------------------------

result_df = pd.DataFrame(results)


print("\nCandidate Matching Results:")
print(result_df.head(10))


# --------------------------------------------------
# 12. Sort candidates by matched skills
# --------------------------------------------------

result_df = result_df.sort_values(
    by="Match_Count",
    ascending=False
)


print("\nTop Matching Candidates:")
print(result_df.head(10))


# --------------------------------------------------
# 13. Calculate Skill Score
# --------------------------------------------------

total_required_skills = len(
    job_requirements["skills"]
)


result_df["Skill_Score"] = (
    result_df["Match_Count"]
    / total_required_skills
) * 100


print("\nTop Candidates with Skill Score:")

print(
    result_df[
        [
            "ID",
            "Category",
            "Matched_Skills",
            "Match_Count",
            "Skill_Score"
        ]
    ].head(10)
)


# --------------------------------------------------
# 14. Required Experience
# --------------------------------------------------

required_experience = int(
    job_requirements["experience"]
)


# --------------------------------------------------
# 15. Experience Matching
# --------------------------------------------------

experience_matches = []

for index in result_df.index:

    candidate_experience = resume_df.loc[
        index,
        "Experience"
    ]

    if candidate_experience != "Not Mentioned":

        candidate_experience = int(
            candidate_experience
        )

        if candidate_experience >= required_experience:

            experience_matches.append(1)

        else:

            experience_matches.append(0)

    else:

        experience_matches.append(0)


# Add experience match column
result_df["Experience_Match"] = experience_matches


print("\nExperience Matching:")

print(
    result_df[
        [
            "ID",
            "Category",
            "Match_Count",
            "Skill_Score",
            "Experience_Match"
        ]
    ].head(10)
)


# --------------------------------------------------
# 16. Education Matching
# --------------------------------------------------

education_matches = []

for index in result_df.index:

    candidate_education = resume_df.loc[
        index,
        "Education"
    ]

    candidate_education = str(
        candidate_education
    ).lower()


    if (
        "b.tech" in candidate_education
        or "btech" in candidate_education
        or "b.e" in candidate_education
        or "be" in candidate_education
        or "bca" in candidate_education
        or "b.sc" in candidate_education
        or "bsc" in candidate_education
        or "b.com" in candidate_education
        or "bcom" in candidate_education
        or "bachelor" in candidate_education
    ):

        education_matches.append(1)

    else:

        education_matches.append(0)


# Add education match column
result_df["Education_Match"] = education_matches


print("\nEducation Matching:")

print(
    result_df[
        [
            "ID",
            "Category",
            "Match_Count",
            "Skill_Score",
            "Experience_Match",
            "Education_Match"
        ]
    ].head(10)
)


# --------------------------------------------------
# 17. Calculate Final Matching Score
# --------------------------------------------------

result_df["Final_Score"] = (

    result_df["Skill_Score"] * 0.60

    + result_df["Experience_Match"] * 20

    + result_df["Education_Match"] * 20

)


# --------------------------------------------------
# 18. Sort by Final Score
# --------------------------------------------------

result_df = result_df.sort_values(
    by="Final_Score",
    ascending=False
)


print("\nFinal Candidate Ranking:")

print(
    result_df[
        [
            "ID",
            "Category",
            "Matched_Skills",
            "Skill_Score",
            "Experience_Match",
            "Education_Match",
            "Final_Score"
        ]
    ].head(10)
)


# --------------------------------------------------
# 19. Save Final Candidate Ranking
# --------------------------------------------------

result_df.to_csv(
    "data/results/candidate_ranking.csv",
    index=False
)


print(
    "\nCandidate ranking saved successfully!"
)