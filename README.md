# Pay Equity Audit Lab: Unexplained-Disparity Detection (synthetic data + rules engine)

An end-to-end, fully synthetic workflow that **compares compensation against role, level, location and documented factors
to identify unexplained pay disparities**. It generates master data, effective-dated salary histories, documented pay factors,
derived compa-ratios and comparable groups, adjustment proposals with an approval trail, labelled edge cases and a separate ground truth.
It then validates everything, scores the detection rules against the ground truth, and proves fixed-seed reproducibility.

* **Stack:** Python 3.10+, `numpy`, `pandas` (tests: `pytest`). No network access, no external data.
* **Optional dashboard:** React 18, JavaScript, Vite, Tailwind CSS, Lucide icons, with hand-built HTML/CSS charts.
* **Data output:** CSV, JSON and SQL files (DDL + seed data, tested by loading into SQLite). No database server is required.
* **One generator, any scale:** `--employees 200` (starter) and `--employees 5000` (full) run the same code.

## Reviewer guide

| Question | Where |
|---|---|
| How do I run and verify it? | **Quick start** below (Python only; Node is *not* needed for the core) |
| Problem, assumptions, trade-offs, testing, limitations | [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md) |
| Which AI was used, how, and what I verified | [`AI_USAGE.md`](AI_USAGE.md) and [`ai/prompt_history.md`](ai/prompt_history.md) |
| Data dictionary / ERD / schema | `docs/` |
| Optional dashboard (not required by the brief) | `dashboard/` (React + JavaScript) |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate          # optional
pip install -r requirements.txt

# full dataset (5,000 employees) - the exact command used for data/full
python -m generator --seed 20261022 --employees 5000 --out data/full --docs docs
# starter dataset (200 employees)
python -m generator --seed 20261022 --employees 200 --out data/starter

python -m pytest -q                       # 18 tests (python tests/run_without_pytest.py works too)
./reproducibility_check.sh                # regenerate twice, compare row counts + SHA-256 of all files
```

The CLI exits non-zero if validation fails. Runtime: about 2 s for 5,000 employees.

## What is produced (`data/<scale>/`)

| Path | Content |
|---|---|
| `csv/`, `json/` | 15 tables (see data model). BOOLEAN columns are `0/1`, dates ISO-8601, money in local currency per year |
| `sql/schema.sql`, `sql/seed.sql` | DDL (PK/FK/CHECK, FKs deferrable) + INSERT seed data; loads into SQLite with `PRAGMA foreign_key_check` clean |
| `ground_truth/ground_truth.csv/.json` | Every injected anomaly: entity, `issue_type`, detection rule, expected decision. **Never joined into input tables** |
| `outputs/pay_gap_analysis.csv` | Per-employee expected pay, unexplained gap (robust z), flag, confidence, exception queue |
| `outputs/validation_summary.json` | All validation checks (253 checks, ~968k rows examined for the full set) |
| `outputs/evaluation_metrics.json` | Detection precision/recall per issue type + distribution statistics |
| `manifest/source_manifest.json`, `checksums.json` | Provenance (no external data) and SHA-256 of every output |

Docs: `docs/data_dictionary.md` (every field: type, required, allowed values, unit, uniqueness, rule, FK),
`docs/erd.md` (Mermaid ERD), `docs/schema.sql`. A copy of the full-data validation result is in `validation_summary.json`;
the reproducibility result is in `reproducibility_report.json`.

## React + JavaScript dashboard

A focused Vite + React + JavaScript + Tailwind CSS dashboard lives in `dashboard/`. It shows the verdict, detection quality, anomalies and record trails;
the full tables are in `data/`. Tabs: Overview, Validation, Anomalies vs ground truth, Pay gaps & proposals.
Click any `EMP-`, `CRS-`, `ADJ-`, `CG-` ID (or use the search box) for the full record trail. Each tab has its own link (for example `#validation`), and the
header button switches between light and dark mode.

Requires **Node.js 18+**. Generate the data once from the repo root (see Quick start), then:

```bash
cd dashboard
npm install
npm run dev        # open http://localhost:5173
```

`npm run build` + `npm run preview` serves a production build. Use another dataset with
`$env:DATA_DIR="C:\full\path\data\starter"; npm run dev` (PowerShell) or `DATA_DIR=/path/data/starter npm run dev`.
It must be served over http, because the data is loaded with `fetch`.

## Data model (15 tables)

Master: **Role** (20, 6 families) · **Level** (L1-L10 -> 200 role/level combinations) · **Location** (8, 6 currencies) ·
**FXRate** · **CompensationBand** (one per role x level x location x year, 2024-2026; older versions are `EXPIRED`).
Transactions/events: **Employee** · **Tenure** (1:1) · **SalaryRecord** (effective-dated, append-only) · **PerformanceEvidence** ·
**Promotion** · **CompaRatioSnapshot** · **ComparableGroup** + **ComparableGroupMember** (the **N:M bridge**) ·
**AdjustmentProposal** · **ApprovalEvent** (append-only audit trail).

IDs: `EMP-000001`, `BAND-<role>-<level>-<location>-<year>` (e.g. `BAND-SWE-L3-DEL-2026`), `SAL-<employee-id>-<year>-<seq>`
(e.g. `SAL-EMP-000001-2026-01`), `ADJ-2026-000001`, plus `TEN-`, `PRM-`, `PEV-`, `AEV-`, `CRS-`, `CG-`. Counters are zero-padded,
IDs are never reused, and every referenced ID is validated.

Cardinality highlights: Employee 1:N SalaryRecord; Employee 1:1 Tenure; Band 1:N SalaryRecord; Employee **N:M** ComparableGroup
(bridge); Proposal 1:N ApprovalEvent; APPLIED Proposal 1:1 new SalaryRecord (`adjustment_id`); Promotion 1:1 SalaryRecord.
Optional relationships: `manager_id`, `termination_date`, `supersedes_band_id`, `promotion_id`, `adjustment_id`.
The position (role/level/location) is stored on each effective-dated SalaryRecord rather than overwritten on Employee.

## Business rules and why

1. **Bands are effective-dated.** One version per year; a salary is always matched to the band effective on its `effective_from`.
   Why: comparing 2026 pay to a 2025 band silently overstates compa-ratios.
2. **Pay is generated from documented factors**: `band_mid x exp(0.05*(rating-3) + 0.012*min(tenure,15) + noise) x (1 + approved premiums)`.
   Raises at annual review never cut pay; promotions add 8-15%; relocations re-price in the new location and currency; part-time
   changes keep FTE-equivalent pay constant. Why: variation is *explainable*, so what the model cannot explain is meaningful.
3. **Normalisation.** FTE-equivalent salary = `base_salary / fte`; USD = `x fx_rate`. Compa-ratio = `normalized / band_mid_usd`;
   range position = `(normalized - min) / (max - min)`.
4. **Comparable groups (rule R1):** same role family + level + location; a group needs >= 5 members (`min_size_met`), smaller
   groups are kept but their flags get `confidence = LOW`. Manual cross-family groups require a written rationale.
5. **Expected pay and unexplained gap.** A robust (iteratively re-weighted) regression of `log(compa-ratio)` on rating, tenure and documented
   premium; residual z-score uses MAD; flag when `|z| > 3.5`. The recovered coefficients on the full set are rating 0.048 (true 0.05),
   tenure 0.0119 (true 0.012), premium 1.01 (true 1.0), which shows the factors really explain pay.
6. **Exception path.** Rows with a methodology defect (expired band, FTE ignored, FX missing) are routed to an exception queue and
   **excluded from the model and from proposals**, so bad comparisons never create pay changes.
7. **Proposals.** For each flag: `proposed = pay explained by documented factors`. Lifecycle `DRAFT -> SUBMITTED -> MANAGER_APPROVED ->
   HR_APPROVED -> APPLIED` (or `REJECTED`). Rules: reductions are rejected ("no pay cuts", referred to committee); increases above 35%
   stop at `HR_APPROVED` (committee sign-off); other proposals advance on fixed SLA offsets (+1/+4/+8/+10 days) up to the AS_OF date.
   `APPLIED` adds a **new SalaryRecord**; history is never overwritten.
8. **Ground truth comes from rules, not random labels.** Outlier labels derive from the off-cycle event that created them; every other label
   derives from the specific field combination the injector changed.

## Injected edge cases (labelled in `ground_truth/`)

| issue_type | How it is injected | Rule that detects it | Full-data result (precision / recall) |
|---|---|---|---|
| `UNEXPLAINED_OUTLIER` (75) | off-cycle x1.22-1.35 or x0.70-0.80 with no documented factor | `abs(z) > 3.5` after documented-factor model | 0.96 / 1.00 |
| `EXPIRED_BAND_COMPARISON` (40) | snapshot compares against the 2025 band | `band.effective_to < snapshot_date` | 1.00 / 1.00 |
| `FTE_IGNORED` (40) | part-timer compa-ratio from raw pay | `fte_applied = 0 and fte < 1` | 1.00 / 1.00 |
| `CURRENCY_CONVERSION_MISSING` (30) | INR/GBP/EUR/... salary vs a USD band, no FX | `currency != USD and fx_applied = 0` | 1.00 / 1.00 |
| `ADJUSTMENT_WITHOUT_APPROVAL` (7) | `APPLIED` with manager/HR approval events skipped | status APPLIED without approval events | 1.00 / 1.00 |
| `INCOMPARABLE_GROUP_NO_RATIONALE` (8) | manual group mixes role families, rationale null | families > 1 and rationale null | 1.00 / 1.00 |

Anomalies are about 4% of snapshot rows, their targets are disjoint, and injection changes only the labelled row (a valid manual group
*with* a rationale is included as a negative control). The 3 outlier false positives are real noise-tail cases (for example an employee priced at a neutral rating whose later
rating is low, where the no-pay-cut policy keeps pay up), not defects.

## Validation (`generator/validate.py`)

253 checks: PK uniqueness/null; ID formats; **FK integrity on every join**; required fields and allowed enums; date ordering (hire <= first
salary, contiguous non-overlapping effective ranges, closed at termination, band version years); salary-to-band-to-location consistency;
change-reason consistency (promotion level +1 and pct reconciles, FTE change keeps pay, relocation changes currency); tenure reconciliation;
**arithmetic reconciliation** of every snapshot row (salary used, FX, band USD values, compa-ratio, range position) and every proposal;
group counts and R1 membership; **legal lifecycle transitions** and event order; duplicates; ground-truth IDs exist; **no ground-truth
column in any input table**.

Findings that hit a labelled anomaly are classed as *expected*; anything else is an *unexpected error*. Status is `PASS` only if
`unexpected_errors = 0` and `missed_labelled = 0`. The full dataset: **PASS, 0 unexpected errors, 139 expected findings observed**.

## Reproducibility

One `numpy.random.default_rng(20261022)`, no wall-clock time, no unordered iteration, rows sorted by primary key before writing.
`./reproducibility_check.sh` runs the generator twice into temp dirs and compares per-table row counts and SHA-256 checksums of all 38
output files: **REPRODUCIBLE** (see `reproducibility_report.json`). Changing `--seed` changes the data; changing `--employees` rescales it.

## Tests (`tests/`)

ID formats; same seed -> identical frames and identical checksums; compa-ratio / range-position / FTE / FX math on known inputs; effective-dated
bands (200 role/level combinations, expired versions); every injected anomaly is detected by rules; anomalies disjoint and rare; a valid manual
group is not flagged; validation passes on good data and **fails on deliberately broken rows** (FK, enum, arithmetic, dates, duplicate PK,
derived value, missing approval); ground truth not leaked; applied proposals add records without overwriting; coverage of normal/boundary/
failure cases; realistic distributions; SQL seed loads into SQLite with FKs enforced; scale parameter.

## Assumptions and limitations

* All data, names of cities and FX rates are synthetic; FX is one rate per currency per year (not daily).
* The model is intentionally simple and transparent (robust regression + z-score), which is appropriate for audit trails. It does not use
  protected attributes; adding them would be the next step for a legal pay-equity analysis.
* Approval stage timing uses fixed SLA offsets from creation; the AS_OF date is fixed at 2026-10-22 (snapshot 2026-10-01).
* Tiny groups (< 5) are reported, not hidden; flags in them are marked `LOW` confidence.

## Provenance and lawful use

No external data is used (`manifest/source_manifest.json`: `external_data_used = false`). No personal or confidential information exists in
the dataset. Public pay-equity concepts (compa-ratio, range penetration) were used for schema inspiration only.

## Repository layout

```
pay-equity-audit-lab/
├── ai/
│   └── prompt_history.md            # AI prompts used on this project
├── dashboard/                       # Optional React + Tailwind CSS viewer
│   ├── scripts/
│   │   └── sync-data.mjs            # Copies a generated dataset into public/data
│   ├── src/
│   │   ├── App.jsx                  # Page layout, navigation and search
│   │   ├── Trace.jsx                # Record trail for a clicked ID
│   │   ├── data.js                  # Loads the generated data
│   │   ├── main.jsx                 # React entry point
│   │   ├── styles.css               # Tailwind setup, colours, dark mode
│   │   ├── tabs.jsx                 # Overview, Validation, Anomalies, Pay gaps
│   │   └── ui.jsx                   # Cards, tables, chart and side panel
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
├── data/
│   ├── full/                        # 5,000 employees
│   │   ├── csv/                     # 15 tables
│   │   ├── json/                    # The same 15 tables
│   │   ├── ground_truth/            # ground_truth.csv, ground_truth.json
│   │   ├── manifest/                # source_manifest.json
│   │   ├── outputs/                 # evaluation_metrics.json, pay_gap_analysis.csv, validation_summary.json
│   │   ├── sql/                     # schema.sql, seed.sql
│   │   └── checksums.json           # SHA-256 of every output
│   └── starter/                     # 200 employees, same layout as full/
├── docs/
│   ├── DESIGN_DECISIONS.md          # Assumptions, trade-offs, testing, limitations
│   ├── data_dictionary.md
│   ├── erd.md
│   └── schema.sql
├── generator/                       # Python pipeline: run with python -m generator
│   ├── __init__.py
│   ├── __main__.py                  # Command-line entry point
│   ├── analysis.py                  # Compa-ratio model and unexplained-gap flags
│   ├── anomalies.py                 # Labelled edge-case injection
│   ├── build.py                     # Runs the generation steps in order
│   ├── config.py                    # Run configuration
│   ├── docs.py                      # Writes docs from the schema
│   ├── evaluate.py                  # Precision, recall and distributions
│   ├── export.py                    # Writes CSV, JSON, SQL and checksums
│   ├── history.py                   # Effective-dated salary history
│   ├── master_data.py               # Roles, levels, locations, FX, bands
│   ├── proposals.py                 # Adjustment proposals and approvals
│   ├── reference.py                 # Reference values and pay coefficients
│   ├── rules.py                     # Detection rules
│   ├── schema.py                    # Table definitions
│   └── validate.py                  # Validation checks
├── tests/
│   ├── conftest.py
│   ├── helpers.py
│   ├── run_without_pytest.py
│   └── test_pipeline.py
├── .gitignore
├── AI_USAGE.md
├── LICENSE
├── README.md
├── reproducibility_check.sh
├── reproducibility_report.json
├── requirements.txt
└── validation_summary.json
```

Generated or local files such as `.venv/`, `dashboard/node_modules/`, `dashboard/dist/` and `dashboard/public/data/` are ignored by Git, so they aren't listed.
