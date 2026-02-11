import pandas as pd
import re
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# -------------------------
# 1. Helpers
# -------------------------
def clean_text(text: str) -> str:
    """Basic cleaning (lowercase, remove special chars)."""
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text.strip()

def build_room_type(row):
    """Build room_type_all from Room Type, Breakfast, Nonref, Occupancy."""
    result = str(row["Room Type"]).lower()
    if row.get("Breakfast", 0) == 1:
        result += " br"
    if row.get("Nonref", 0) == 1:
        result += " nonref"
    # Add occupancy number
    match = re.search(r'\d+', str(row.get("Occupancy", "")))
    if match:
        result += f" {match.group(0)}"
    return result

def combined_similarity(text_sim, area1, area2, occ1, occ2, alpha=0.6, beta=0.2, gamma=0.2):
    """
    Weighted similarity: text + area + occupancy.
    alpha + beta + gamma = 1
    """
    # area similarity
    if area1 and area2:
        area_sim = 1 - abs(area1 - area2) / max(area1, area2)
        area_sim = max(area_sim, 0)
    else:
        area_sim = 0

    # occupancy similarity
    if occ1 and occ2:
        occ_sim = 1 - abs(occ1 - occ2) / max(occ1, occ2)
        occ_sim = max(occ_sim, 0)
    else:
        occ_sim = 0

    return alpha * text_sim + beta * area_sim + gamma * occ_sim

def extract_occupancy(val):
    match = re.search(r'\d+', str(val))
    return int(match.group(0)) if match else None


# -------------------------
# 2. Load your datasets
# -------------------------
my_df = pd.read_excel("C:/Users/42072/Desktop/program/scrapy_Karlova_cz.xlsx")
comp_df = pd.read_excel("C:/Users/42072/Desktop/program/2025-10-13_nicer.xlsx") 
# -------------------------
# 3. Preprocess
# -------------------------
comp_df["Area"] = comp_df["Area"].fillna(14)

my_df["room_type_all"] = my_df.apply(build_room_type, axis=1)
comp_df["room_type_all"] = comp_df.apply(build_room_type, axis=1)

# Build full description = Room Type + Highlights
my_df["full_desc"] = (my_df["room_type_all"].fillna("") + " " +
                      my_df["Highlights"].fillna("")).apply(clean_text)

comp_df["full_desc"] = (comp_df["room_type_all"].fillna("") + " " +
                        comp_df["Highlights"].fillna("")).apply(clean_text)


my_df["occ_num"] = my_df["Occupancy"].apply(extract_occupancy)
comp_df["occ_num"] = comp_df["Occupancy"].apply(extract_occupancy)

# -------------------------
# 4. Embeddings
# -------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")
my_embeds = model.encode(my_df["full_desc"].tolist(), convert_to_numpy=True)
comp_embeds = model.encode(comp_df["full_desc"].tolist(), convert_to_numpy=True)

# -------------------------
# 5. Matching
# -------------------------
similarity_matrix = cosine_similarity(my_embeds, comp_embeds)

my_df = my_df.reset_index(drop=True)
comp_df = comp_df.reset_index(drop=True)
# -------------------------
# 5. Matching (per check-in date)
# -------------------------
matches = []

for checkin_date, comp_group in comp_df.groupby("Checkin"):
    print(f"\n🔍 Matching for check-in date: {checkin_date}")

    # Compute similarities only within this subset
    comp_embeds_subset = model.encode(comp_group["full_desc"].tolist(), convert_to_numpy=True)
    sim_matrix_subset = cosine_similarity(my_embeds, comp_embeds_subset)

    comp_group = comp_group.reset_index(drop=True)

    for j, comp_row in comp_group.iterrows():
        best_match_idx = None
        best_score = -1
        for i, my_row in my_df.iterrows():
            text_sim = sim_matrix_subset[i, j]
            final_score = combined_similarity(
                text_sim,
                my_row["Area"],
                comp_row["Area"],
                my_row["occ_num"],
                comp_row["occ_num"],
                alpha=0.6, beta=0.2, gamma=0.2
            )
            if final_score > best_score:
                best_score = final_score
                best_match_idx = i

        if best_match_idx is not None and best_score >= 0.84:
            my_row_best = my_df.loc[best_match_idx]
            matches.append({
                "Checkin": comp_row.get("Checkin"),
                "Checkout": comp_row.get("Checkout"),
                "Competitor Room": comp_row["Room Type"],
                "Competitor Highlights": comp_row["Highlights"],
                "Competitor Link": comp_row.get("Hotel Link", ""),
                "Competitor Area": comp_row.get("Area"),
                "Competitor Occupancy": comp_row["occ_num"],
                "Competitor Breakfast": comp_row.get("Breakfast", 0),
                "Competitor Nonref": comp_row.get("Nonref", 0),
                "Competitor Price": comp_row["Price"],
                "Scraping Date": comp_row["Scraping Date"],

                "My Room": my_row_best["Room Type"],
                "My Highlights": my_row_best["Highlights"],
                "My Area": my_row_best.get("Area"),
                "My Occupancy": my_row_best["occ_num"],
                "My Breakfast": my_row_best.get("Breakfast", 0),
                "My Nonref": my_row_best.get("Nonref", 0),

                "Similarity": round(best_score, 3)
            })
        else:
            print(f"   No strong match for {comp_row['Room Type']} (best={round(best_score,3)})")





results_df = pd.DataFrame(matches)
filtered_df = results_df[~results_df["Competitor Link"].str.contains("karlova-prague", case=False, na=False)]
removed_df = results_df[results_df["Competitor Link"].str.contains("karlova-prague", case=False, na=False)]

# Save both into one Excel file
output_path = "C:/Users/42072/Desktop/program/2025-10-13x.xlsx"
with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
    filtered_df.to_excel(writer, sheet_name="Filtered Results", index=False)
    removed_df.to_excel(writer, sheet_name="Removed Karlova", index=False)

print(f"Saved results to {output_path}")
print(f"Filtered rows: {len(filtered_df)}, Removed rows: {len(removed_df)}")

