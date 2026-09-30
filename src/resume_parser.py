import pandas as pd
import re
from nltk.tokenize import word_tokenize

# Dataset load
df = pd.read_csv("data/resume/Resume.csv/Resume.csv")

print(df.head())
print(df.shape)
print(df.columns)

# Missing values check
print("\nMissing values:")
print(df.isnull().sum())

# Duplicate check
print("\nDuplicate resumes:")
print(df["Resume_str"].duplicated().sum())

# Number of categories
print("\nNumber of categories:")
print(df["Category"].nunique())

# Category counts
print("\nCategory counts:")
print(df["Category"].value_counts())

# Remove duplicate resumes
df = df.drop_duplicates(subset=["Resume_str"])

print("\nAfter removing duplicates:")
print(df.shape)

# Convert resume text to lowercase
df["Clean_Resume"] = df["Resume_str"].str.lower()

# Remove extra spaces and new lines
df["Clean_Resume"] = df["Clean_Resume"].apply(
    lambda x: re.sub(r"\s+", " ", x).strip()
)

# Remove unnecessary special characters
df["Clean_Resume"] = df["Clean_Resume"].apply(
    lambda x: re.sub(r"[^a-zA-Z0-9\s\+\#\.\-\/]", " ", x)
)

print("\nAfter special character cleaning:")
print(df["Clean_Resume"].iloc[0][:300])

print("\nTOKENIZATION STARTING...")

# Tokenization
df["Tokens"] = df["Clean_Resume"].apply(word_tokenize)

print("\nTokens:")
print(df["Tokens"].iloc[0][:20])


# Skills list
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
    "accounting"
]


# Extract skills from each resume
def extract_skills(text):
    found_skills = []

    for skill in skills:
        if skill in text:
            found_skills.append(skill)

    return found_skills


# Apply skill extraction
df["Skills"] = df["Clean_Resume"].apply(extract_skills)

print("\nExtracted Skills:")
print(df[["Category", "Skills"]].head())


# Experience extraction
def extract_experience(text):
    pattern = r"\b(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b"

    match = re.search(pattern, text)

    if match:
        return match.group(1)

    return "Not Mentioned"


# Apply experience extraction
df["Experience"] = df["Clean_Resume"].apply(extract_experience)

print("\nExperience:")
print(df[["Category", "Experience"]].head())


# Education extraction
def extract_education(text):
    education = []

    education_keywords = [
        "b.tech",
        "btech",
        "b.e",
        "be",
        "bachelor of technology",
        "bachelor of engineering",
        "bca",
        "bachelor of computer applications",
        "b.sc",
        "bsc",
        "bachelor of science",
        "b.com",
        "bcom",
        "bachelor of commerce",
        "m.tech",
        "mtech",
        "master of technology",
        "m.e",
        "me",
        "mca",
        "master of computer applications",
        "m.sc",
        "msc",
        "master of science",
        "m.b.a",
        "mba",
        "master of business administration",
        "phd",
        "doctorate",
        "12th",
        "10th"
    ]

    for keyword in education_keywords:
        if keyword in text:
            education.append(keyword)

    if education:
        return ", ".join(education)

    return "Not Mentioned"


# Apply education extraction
df["Education"] = df["Clean_Resume"].apply(extract_education)

print("\nEducation:")
print(df[["Category", "Education"]].head())


# Improved name extraction
def extract_name(text):
    words = text.split()

    # Common words that are usually not candidate names
    ignore_words = [
        "resume",
        "curriculum",
        "vitae",
        "hr",
        "administrator",
        "specialist",
        "manager",
        "director",
        "engineer",
        "developer",
        "consultant",
        "accountant",
        "teacher",
        "designer",
        "summary",
        "objective",
        "profile",
        "experience",
        "professional"
    ]

    # Check first few words
    for i in range(min(5, len(words) - 1)):
        first = words[i]
        second = words[i + 1]

        if first not in ignore_words and second not in ignore_words:
            return first + " " + second

    return "Not Mentioned"

# Apply name extraction
df["Name"] = df["Clean_Resume"].apply(extract_name)

print("\nName:")
print(df[["Category", "Name"]].head())


# Save final cleaned dataset
df.to_csv("data/resume/cleaned_resume.csv", index=False)

print("\nFinal cleaned dataset saved successfully!")