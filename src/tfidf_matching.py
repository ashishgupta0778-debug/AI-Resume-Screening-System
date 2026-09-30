import pandas as pd
import math
from collections import Counter


# --------------------------------------------------
# 1. Load cleaned resume dataset
# --------------------------------------------------

resume_df = pd.read_csv("data/resume/cleaned_resume.csv")


# --------------------------------------------------
# 2. Load Job Description
# --------------------------------------------------

with open("data/jobs/software_developer.txt", "r") as file:
    job_description = file.read()


print("Number of resumes:", len(resume_df))
print("\nJob Description loaded successfully!")


# --------------------------------------------------
# 3. Convert resume text into words
# --------------------------------------------------

resume_documents = []

for text in resume_df["Clean_Resume"]:

    # Convert value to string so NaN does not cause error
    words = str(text).split()

    resume_documents.append(words)


# Convert Job Description into words
jd_words = job_description.lower().split()


print("\nText converted into words successfully!")
print("First resume words:", resume_documents[0][:20])
print("JD words:", jd_words[:20])


# --------------------------------------------------
# 4. Calculate Term Frequency (TF)
# --------------------------------------------------

def calculate_tf(words):

    word_count = Counter(words)

    total_words = len(words)

    tf = {}

    for word, count in word_count.items():

        tf[word] = count / total_words

    return tf


# TF of first resume
first_resume_tf = calculate_tf(resume_documents[0])

print("\nTF of first resume:")
print(list(first_resume_tf.items())[:10])


# TF of Job Description
jd_tf = calculate_tf(jd_words)

print("\nTF of Job Description:")
print(list(jd_tf.items())[:10])


# --------------------------------------------------
# 5. Calculate IDF
# --------------------------------------------------
# --------------------------------------------------
# 5. Calculate IDF efficiently
# --------------------------------------------------

total_documents = len(resume_documents)

document_frequency = Counter()

for document in resume_documents:

    unique_words = set(document)

    for word in unique_words:
        document_frequency[word] += 1


idf = {}

for word, document_count in document_frequency.items():

    idf[word] = math.log(
        (total_documents + 1) / (document_count + 1)
    ) + 1


print("\nIDF calculation successful!")
print("Total unique words:", len(idf))



print("\nIDF calculation successful!")
print("Total unique words:", len(idf))


# --------------------------------------------------
# 6. Calculate TF-IDF for first resume
# --------------------------------------------------

first_resume_tfidf = {}

for word, tf_value in first_resume_tf.items():

    if word in idf:

        first_resume_tfidf[word] = (
            tf_value * idf[word]
        )


print("\nTF-IDF of first resume:")
print(list(first_resume_tfidf.items())[:10])


# --------------------------------------------------
# 7. Calculate TF-IDF for Job Description
# --------------------------------------------------

jd_tfidf = {}

for word, tf_value in jd_tf.items():

    if word in idf:

        jd_tfidf[word] = (
            tf_value * idf[word]
        )


print("\nTF-IDF of Job Description:")
print(list(jd_tfidf.items())[:10])


# --------------------------------------------------
# 8. Calculate Cosine Similarity
# --------------------------------------------------

def cosine_similarity(vector1, vector2):

    common_words = (
        set(vector1.keys()) &
        set(vector2.keys())
    )

    # Dot product
    dot_product = 0

    for word in common_words:

        dot_product += (
            vector1[word] * vector2[word]
        )


    # Magnitude of vector 1
    magnitude1 = math.sqrt(
        sum(
            value * value
            for value in vector1.values()
        )
    )


    # Magnitude of vector 2
    magnitude2 = math.sqrt(
        sum(
            value * value
            for value in vector2.values()
        )
    )


    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:

        return 0


    return dot_product / (
        magnitude1 * magnitude2
    )


# --------------------------------------------------
# 9. Calculate similarity for all resumes
# --------------------------------------------------

similarity_results = []

for i in range(len(resume_documents)):

    # Calculate TF for current resume
    resume_tf = calculate_tf(resume_documents[i])

    # Calculate TF-IDF for current resume
    resume_tfidf = {}

    for word, tf_value in resume_tf.items():

        if word in idf:

            resume_tfidf[word] = (
                tf_value * idf[word]
            )

    # Calculate cosine similarity
    similarity = cosine_similarity(
        resume_tfidf,
        jd_tfidf
    )

    similarity_results.append(similarity)


# Add similarity scores to dataframe
resume_df["TFIDF_Similarity"] = similarity_results


# Sort resumes by similarity
resume_df = resume_df.sort_values(
    by="TFIDF_Similarity",
    ascending=False
)


print("\nTop 10 TF-IDF Matching Resumes:")

print(
    resume_df[
        [
            "Category",
            "TFIDF_Similarity"
        ]
    ].head(10)
)
# --------------------------------------------------
# 10. Save TF-IDF similarity results
# --------------------------------------------------

resume_df.to_csv(
    "data/results/tfidf_similarity.csv",
    index=False
)

print("\nTF-IDF similarity results saved successfully!")