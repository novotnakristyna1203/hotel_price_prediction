import pandas as pd
import ast
import re

# Load the Excel file
df = pd.read_excel("C:/Users/42072/Desktop/program/2025-10-13.xlsx")


df['Breakfast'] = df['Other Info'].str.contains("snídaně v ceně", case=False, na=False).astype(int)
df['Nonref'] = df['Other Info'].str.contains("nevratná rezervace", case=False, na=False).astype(int)
df['Ref'] = df['Other Info'].str.contains("zrušení zdarma", case=False, na=False).astype(int)

df['Room Type'] = df['Room Type'].replace("N/A", pd.NA).ffill()

# If Highlights are saved as strings like "['Pokoj','Minibar']",
# convert them back to Python lists
if df['Highlights'].dtype == object:
    df['Highlights'] = df['Highlights'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith("[") else x)

# Loop through rows and forward-fill Highlights when empty
for i in range(1, len(df)):
    if isinstance(df.at[i, 'Highlights'], list) and len(df.at[i, 'Highlights']) == 0:
        df.at[i, 'Highlights'] = df.at[i-1, 'Highlights']

for i, highlights in df['Highlights'].items():
    if isinstance(highlights, list):
        for h in highlights:
            match = re.search(r"(\d+)\s*m²", h)
            if match:
                df.at[i, 'Area'] = int(match.group(1))  # store as number
                break  # stop after finding the first match

def extract_price(val):
    if pd.isna(val):
        return None
    # Remove all non-digit characters except decimal separators
    num_str = re.sub(r"[^\d,\.]", "", str(val))
    try:
        return float(num_str)
    except:
        return None

df['Price'] = df['Price'].apply(extract_price)

def extract_max_occupancy(val):
    if pd.isna(val):
        return None
    match = re.search(r"(\d+)", str(val))
    if match:
        return int(match.group(1))
    return None

df['Occupancy'] = df['Occupancy'].apply(extract_max_occupancy)


print(df.head())


df.to_excel("C:/Users/42072/Desktop/program/2025-10-13_nicer.xlsx", index=False)
