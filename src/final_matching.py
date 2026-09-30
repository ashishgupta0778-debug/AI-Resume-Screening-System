import pandas as pd


# Load existing candidate ranking results
candidate_df = pd.read_csv(
    "data/results/candidate_ranking.csv"
)

# Load TF-IDF similarity results
tfidf_df = pd.read_csv(
    "data/results/tfidf_similarity.csv"
)


print("Candidate ranking loaded successfully!")
print("TF-IDF results loaded successfully!")

print("\nCandidate Ranking Shape:")
print(candidate_df.shape)

print("\nTF-IDF Results Shape:")
print(tfidf_df.shape)

print("\nCandidate Ranking Columns:")
print(candidate_df.columns.tolist())

print("\nTF-IDF Results Columns:")
print(tfidf_df.columns.tolist())

# Merge Candidate Ranking and TF-IDF results using ID

merged_df = pd.merge(
    candidate_df,
    tfidf_df[["ID", "TFIDF_Similarity"]],
    on="ID",
    how="inner"
)

print("\nMerged Results Shape:")
print(merged_df.shape)

print("\nMerged Results Columns:")
print(merged_df.columns.tolist())

print("\nMerged Data:")
print(
    merged_df[
        [
            "ID",
            "Category",
            "Final_Score",
            "TFIDF_Similarity"
        ]
    ].head(10)
)

merged_df["TFIDF_Score"] = (
    merged_df["TFIDF_Similarity"] * 100
)

print("\nTF-IDF Score:")
print(
    merged_df[
        ["ID", "Final_Score", "TFIDF_Similarity", "TFIDF_Score"]
    ].head(10)
)
merged_df["Combined_Score"] = (
    merged_df["Final_Score"] * 0.70
    + merged_df["TFIDF_Score"] * 0.30
)

merged_df = merged_df.sort_values(
    by="Combined_Score",
    ascending=False
)

print("\nFinal Combined Ranking:")
print(
    merged_df[
        [
            "ID",
            "Category",
            "Matched_Skills",
            "Skill_Score",
            "Experience_Match",
            "Education_Match",
            "TFIDF_Score",
            "Combined_Score"
        ]
    ].head(10)
)



# Verify final CSV

check_df = pd.read_csv(
    "data/results/final_candidate_ranking.csv"
)

print("\nFinal CSV Loaded Successfully!")
print("Shape:")
print(check_df.shape)

print("\nColumns:")
print(check_df.columns.tolist())

print("\nTop 5 Candidates:")
print(
    check_df[
        [
            "ID",
            "Category",
            "Final_Score",
            "TFIDF_Score",
            "Combined_Score"
        ]
    ].head(5)
)
print("\nTop Candidate Details:")

top_candidate = check_df.iloc[0]

print("ID:", top_candidate["ID"])
print("Category:", top_candidate["Category"])
print("Matched Skills:", top_candidate["Matched_Skills"])
print("Skill Score:", top_candidate["Skill_Score"])
print("Experience Match:", top_candidate["Experience_Match"])
print("Education Match:", top_candidate["Education_Match"])
print("TF-IDF Score:", top_candidate["TFIDF_Score"])
print("Combined Score:", top_candidate["Combined_Score"])

# Create explanation for the top candidates

merged_df["Explanation"] = (
    "Matched Skills: "
    + merged_df["Matched_Skills"].astype(str)
    + " | Experience Match: "
    + merged_df["Experience_Match"].astype(str)
    + " | Education Match: "
    + merged_df["Education_Match"].astype(str)
    + " | TF-IDF Score: "
    + merged_df["TFIDF_Score"].round(2).astype(str)
)

print("\nCandidate Explanation:")
print(
    merged_df[
        [
            "ID",
            "Combined_Score",
            "Explanation"
        ]
    ].head(5)
)

# Save final ranking with explanation

merged_df.to_csv(
    "data/results/final_candidate_ranking.csv",
    index=False
)

print("\nFinal candidate ranking with explanation saved successfully!")