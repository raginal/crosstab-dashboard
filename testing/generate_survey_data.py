import numpy as np
import pandas as pd
from scipy import stats

rng = np.random.default_rng(42)

n = 500

# 1. Respondent_ID
respondent_id = np.arange(1, n + 1)

# 2. Gender (~48/48/4%)
gender = rng.choice(["Male", "Female", "Non-binary"], size=n, p=[0.48, 0.48, 0.04])

# 3. Region (~25% each)
region = rng.choice(["Northeast", "South", "Midwest", "West"], size=n, p=[0.25, 0.25, 0.25, 0.25])

# 4. Age: normal around 42, SD 14, clipped to 18–74
age_raw = rng.normal(42, 14, n)
age = np.clip(np.round(age_raw).astype(int), 18, 74)

# 5. Education (~20/25/30/18/7%)
edu_levels = ["High School", "Some College", "Bachelor's", "Master's", "PhD"]
edu_probs = [0.20, 0.25, 0.30, 0.18, 0.07]
education = rng.choice(edu_levels, size=n, p=edu_probs)
edu_index = np.array([edu_levels.index(e) for e in education])  # 0–4

# 6. Income_K: correlated with Education, range 20–200
# Base income by education level
edu_income_means = [32, 42, 60, 80, 100]
edu_income_sds   = [8,  10, 15, 20, 25]
income_raw = np.array([
    rng.normal(edu_income_means[ei], edu_income_sds[ei])
    for ei in edu_index
])
# Also add mild positive correlation with age
income_raw += (age - 42) * 0.4
income_k = np.clip(np.round(income_raw).astype(int), 20, 200)

# 7. Satisfaction (1–5, ~5/15/30/30/20%); women score slightly higher
base_sat_probs = np.array([0.05, 0.15, 0.30, 0.30, 0.20])
satisfaction = np.empty(n, dtype=float)
for i in range(n):
    if gender[i] == "Female":
        p = np.array([0.04, 0.12, 0.28, 0.34, 0.22])
    elif gender[i] == "Non-binary":
        p = np.array([0.05, 0.14, 0.30, 0.31, 0.20])
    else:
        p = np.array([0.07, 0.18, 0.32, 0.27, 0.16])
    p = p / p.sum()
    satisfaction[i] = rng.choice([1, 2, 3, 4, 5], p=p)
satisfaction = satisfaction.astype(int)

# 8. Would_Recommend (1–7), positively correlated with Satisfaction
# Map satisfaction 1–5 to center of 1–7 scale, add noise
rec_center = 1 + (satisfaction - 1) * (6 / 4)  # maps 1→1, 5→7
rec_raw = rec_center + rng.normal(0, 0.8, n)
would_recommend = np.clip(np.round(rec_raw).astype(int), 1, 7)

# 9. Product_Usage: base ~10/15/25/30/20%; West more, South less
usage_levels = ["Never", "Rarely", "Monthly", "Weekly", "Daily"]
base_usage = np.array([0.10, 0.15, 0.25, 0.30, 0.20])
west_usage  = np.array([0.05, 0.10, 0.20, 0.35, 0.30])
south_usage = np.array([0.18, 0.22, 0.28, 0.22, 0.10])

product_usage = np.empty(n, dtype=object)
for i in range(n):
    if region[i] == "West":
        p = west_usage
    elif region[i] == "South":
        p = south_usage
    else:
        p = base_usage
    p = p / p.sum()
    product_usage[i] = rng.choice(usage_levels, p=p)

# 10. Survey_Weight: 0.5–2.5, varies by Gender and Region
weight_map = {
    ("Male", "Northeast"): 1.8,
    ("Male", "South"): 0.9,
    ("Male", "Midwest"): 1.2,
    ("Male", "West"): 1.5,
    ("Female", "Northeast"): 0.7,
    ("Female", "South"): 1.6,
    ("Female", "Midwest"): 0.8,
    ("Female", "West"): 1.1,
    ("Non-binary", "Northeast"): 2.2,
    ("Non-binary", "South"): 2.3,
    ("Non-binary", "Midwest"): 2.4,
    ("Non-binary", "West"): 2.0,
}
survey_weight = np.array([
    np.clip(
        round(weight_map.get((gender[i], region[i]), 1.0) + rng.normal(0, 0.15), 2),
        0.5, 2.5
    )
    for i in range(n)
])

# Assemble DataFrame
df = pd.DataFrame({
    "Respondent_ID": respondent_id,
    "Gender": gender,
    "Region": region,
    "Age": age,
    "Education": education,
    "Income_K": income_k,
    "Satisfaction": satisfaction,
    "Would_Recommend": would_recommend,
    "Product_Usage": product_usage,
    "Survey_Weight": survey_weight,
})

# Introduce ~3% NaN in all columns except Respondent_ID and Survey_Weight
nullable_cols = ["Gender", "Region", "Age", "Education", "Income_K",
                 "Satisfaction", "Would_Recommend", "Product_Usage"]
total_cells = n * len(nullable_cols)
n_nan = int(round(total_cells * 0.03))
nan_rows = rng.integers(0, n, n_nan)
nan_cols = rng.integers(0, len(nullable_cols), n_nan)
for r, c in zip(nan_rows, nan_cols):
    df.at[r, nullable_cols[c]] = np.nan

# Save to XLSX
out_path = "/Users/harpercohen2/Desktop/python projects/crosstabs/survey_test_data.xlsx"
df.to_excel(out_path, index=False)
print(f"Saved to: {out_path}")

# Verify
import os
assert os.path.exists(out_path), "File not found!"
df_verify = pd.read_excel(out_path)
print(f"Shape: {df_verify.shape}")

# Spot-check correlations and significance
from scipy.stats import spearmanr, chi2_contingency

# Age vs Income_K Spearman
mask = df_verify["Age"].notna() & df_verify["Income_K"].notna()
rho, p_rho = spearmanr(df_verify.loc[mask, "Age"], df_verify.loc[mask, "Income_K"])
print(f"Age × Income_K Spearman rho={rho:.3f}, p={p_rho:.4f}")

# Gender × Satisfaction chi2
ct_gs = pd.crosstab(df_verify["Gender"].dropna(), df_verify["Satisfaction"].dropna())
chi2_gs, p_gs, _, _ = chi2_contingency(ct_gs)
print(f"Gender × Satisfaction chi2={chi2_gs:.2f}, p={p_gs:.4f}")

# Region × Product_Usage chi2
ct_rp = pd.crosstab(df_verify["Region"].dropna(), df_verify["Product_Usage"].dropna())
chi2_rp, p_rp, _, _ = chi2_contingency(ct_rp)
print(f"Region × Product_Usage chi2={chi2_rp:.2f}, p={p_rp:.6f}")

# Survey_Weight: no missing
assert df_verify["Survey_Weight"].isna().sum() == 0, "Survey_Weight has NaNs!"
print("Survey_Weight: no missing values confirmed.")

# NaN rate in nullable columns
nan_rate = df_verify[nullable_cols].isna().mean().mean()
print(f"Overall NaN rate in nullable cols: {nan_rate:.2%}")
