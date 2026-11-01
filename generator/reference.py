"""Reference constants for master data (all synthetic)."""
# code, name, family, L1 USD midpoint, headcount weight
ROLES = [
    ("SWE", "Software Engineer", "ENG", 70000, 18), ("QAE", "QA Engineer", "ENG", 55000, 5),
    ("DEVOPS", "DevOps Engineer", "ENG", 68000, 5), ("DENG", "Data Engineer", "ENG", 70000, 6),
    ("DANL", "Data Analyst", "DATA", 52000, 6), ("DSCI", "Data Scientist", "DATA", 70000, 5),
    ("MLE", "ML Engineer", "DATA", 78000, 3), ("BIAN", "BI Analyst", "DATA", 50000, 4),
    ("PM", "Product Manager", "PRD", 72000, 5), ("UXD", "UX Designer", "PRD", 58000, 4),
    ("TWR", "Technical Writer", "PRD", 45000, 2), ("SREP", "Sales Representative", "GTM", 45000, 8),
    ("ACCM", "Account Manager", "GTM", 52000, 5), ("MKTG", "Marketing Specialist", "GTM", 46000, 4),
    ("OPSA", "Operations Analyst", "OPS", 42000, 5), ("SUPP", "Support Specialist", "OPS", 36000, 7),
    ("ITAD", "IT Administrator", "OPS", 44000, 3), ("HRP", "HR Partner", "PPL", 48000, 4),
    ("ACCT", "Accountant", "PPL", 45000, 3), ("RECR", "Recruiter", "PPL", 42000, 3),
]
FAMILIES = ["ENG", "DATA", "PRD", "GTM", "OPS", "PPL"]
LEVEL_NAMES = ["Associate", "Junior", "Intermediate", "Senior", "Lead", "Principal",
               "Director", "Senior Director", "Vice President", "Senior Vice President"]
LEVEL_STEP = 1.13                      # each level's midpoint is 13% above the previous
# id, city, country, currency, cost-of-living index (vs US=1.0), headcount weight
LOCATIONS = [
    ("DEL", "Delhi", "India", "INR", 0.30, 22), ("BLR", "Bengaluru", "India", "INR", 0.32, 22),
    ("NYC", "New York", "United States", "USD", 1.15, 12), ("AUS", "Austin", "United States", "USD", 1.00, 10),
    ("LON", "London", "United Kingdom", "GBP", 0.95, 10), ("BER", "Berlin", "Germany", "EUR", 0.90, 8),
    ("SIN", "Singapore", "Singapore", "SGD", 0.95, 8), ("TOR", "Toronto", "Canada", "CAD", 0.85, 8),
]
BAND_YEARS = [2024, 2025, 2026]
YEAR_FACTOR = {2024: 1.0, 2025: 1.03, 2026: 1.0609}      # annual band movement
# rate_to_usd (1 unit of currency in USD), synthetic, by year
FX = {
    "USD": {2024: 1.0, 2025: 1.0, 2026: 1.0},
    "GBP": {2024: 1.27, 2025: 1.29, 2026: 1.30},
    "EUR": {2024: 1.08, 2025: 1.09, 2026: 1.10},
    "INR": {2024: 0.0120, 2025: 0.0116, 2026: 0.0112},
    "SGD": {2024: 0.74, 2025: 0.75, 2026: 0.76},
    "CAD": {2024: 0.74, 2025: 0.73, 2026: 0.73},
}
FTE_VALUES = [1.0, 0.8, 0.6, 0.5]
# documented-factor coefficients used to GENERATE pay (the analysis re-estimates them)
RATING_COEF = 0.05      # per rating point vs 3
TENURE_COEF = 0.012     # per year of tenure (cap 15)
