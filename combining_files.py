import pandas as pd
import glob

# Path to all Excel files
files = glob.glob("C:/Users/42072/Desktop/program/today_working_set_matched/processed/*.xlsx")

# Read and combine all sheets
df_list = []
for file in files:
    # read all sheets in each file
    xls = pd.ExcelFile(file)
    for sheet_name in xls.sheet_names:
        temp = pd.read_excel(xls, sheet_name)
        temp["SourceFile"] = file
        temp["SheetName"] = sheet_name
        df_list.append(temp)

# Combine into one long DataFrame
combined = pd.concat(df_list, ignore_index=True)

# Save to a new Excel file
combined.to_excel("C:/Users/42072/Desktop/program/2025-10-14-28.xlsx", index=False)
print("done")