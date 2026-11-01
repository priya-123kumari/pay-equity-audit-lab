"""Single source of truth for the data model.

Drives: CSV/JSON column order, SQL DDL, enum validation and docs/data_dictionary.md.
Column tuple: (name, type, required, allowed, unit, unique, rule, fk)
types: TEXT | INTEGER | REAL | DATE | BOOLEAN   (BOOLEAN exported as 0/1)
"""
from collections import OrderedDict

CHANGE_REASONS = ["HIRE", "ANNUAL_REVIEW", "PROMOTION", "FTE_CHANGE",
                  "RELOCATION_CURRENCY_CHANGE", "OFF_CYCLE_ADJUSTMENT", "PROPOSAL_ADJUSTMENT"]
PROPOSAL_STATUSES = ["DRAFT", "SUBMITTED", "MANAGER_APPROVED", "HR_APPROVED", "APPLIED", "REJECTED"]
# legal lifecycle transitions (None = creation)
TRANSITIONS = {
    None: ["DRAFT"],
    "DRAFT": ["SUBMITTED"],
    "SUBMITTED": ["MANAGER_APPROVED", "REJECTED"],
    "MANAGER_APPROVED": ["HR_APPROVED", "REJECTED"],
    "HR_APPROVED": ["APPLIED", "REJECTED"],
    "APPLIED": [], "REJECTED": [],
}
ISSUE_TYPES = ["UNEXPLAINED_OUTLIER", "EXPIRED_BAND_COMPARISON", "FTE_IGNORED",
               "CURRENCY_CONVERSION_MISSING", "ADJUSTMENT_WITHOUT_APPROVAL",
               "INCOMPARABLE_GROUP_NO_RATIONALE"]

C = lambda name, typ, req=True, allowed=None, unit=None, uniq=False, rule="", fk=None: (name, typ, req, allowed, unit, uniq, rule, fk)
CUR = ["USD", "GBP", "EUR", "INR", "SGD", "CAD"]
FAMS = ["ENG", "DATA", "PRD", "GTM", "OPS", "PPL"]

SCHEMA = OrderedDict()


def table(name, file, pk, desc, card, cols):
    SCHEMA[name] = dict(file=file, pk=pk, desc=desc, cardinality=card, cols=cols)


table("Role", "roles", ["role_id"], "Job role (master data). 20 roles in 6 families.",
      "Role 1:N CompensationBand; Role 1:N SalaryRecord",
      [C("role_id", "TEXT", uniq=True, rule="^[A-Z]{2,6}$"),
       C("role_name", "TEXT", uniq=True), C("role_family", "TEXT", allowed=FAMS, rule="comparability family"),
       C("l1_midpoint_usd", "REAL", unit="USD/yr", rule="> 0; band midpoint at Level 1, US cost of living"),
       C("status", "TEXT", allowed=["ACTIVE", "RETIRED"])])
table("Level", "levels", ["level_id"], "Job level L1..L10 (master data). Midpoint multiplier compounds 13% per level.",
      "Level 1:N CompensationBand; Level 1:N SalaryRecord",
      [C("level_id", "TEXT", uniq=True, rule="^L([1-9]|10)$"), C("level_number", "INTEGER", uniq=True, rule="1..10"),
       C("level_name", "TEXT"), C("midpoint_multiplier", "REAL", rule="1.13^(level_number-1)"),
       C("range_spread_pct", "REAL", unit="fraction", rule="(max-min)/mid; 0.30 at L1 rising to 0.39 at L10")])
table("Location", "locations", ["location_id"], "Pay location with local currency and cost-of-living index.",
      "Location 1:N CompensationBand; Location 1:N SalaryRecord",
      [C("location_id", "TEXT", uniq=True, rule="^[A-Z]{3}$"), C("city", "TEXT"), C("country", "TEXT"),
       C("currency", "TEXT", allowed=CUR), C("col_index", "REAL", rule="> 0; US=1.0"),
       C("status", "TEXT", allowed=["ACTIVE", "CLOSED"])])
table("FXRate", "fx_rates", ["fx_id"], "Effective-dated currency conversion (synthetic) to USD.",
      "Currency 1:N FXRate (one row per currency per year)",
      [C("fx_id", "TEXT", uniq=True, rule="^FX-[A-Z]{3}-\\d{4}$"), C("currency", "TEXT", allowed=CUR),
       C("rate_to_usd", "REAL", unit="USD per 1 unit", rule="> 0"),
       C("effective_from", "DATE"), C("effective_to", "DATE", rule=">= effective_from")])
table("CompensationBand", "compensation_bands", ["band_id"],
      "Effective-dated pay band per role/level/location. One version per year; older versions are EXPIRED.",
      "Role/Level/Location 1:N Band; Band supersedes Band (optional self-reference); Band 1:N SalaryRecord",
      [C("band_id", "TEXT", uniq=True, rule="^BAND-[A-Z]+-L\\d{1,2}-[A-Z]{3}-\\d{4}$ i.e. BAND-<role>-<level>-<location>-<year>"),
       C("role_id", "TEXT", fk="Role.role_id"), C("level_id", "TEXT", fk="Level.level_id"),
       C("location_id", "TEXT", fk="Location.location_id"), C("currency", "TEXT", allowed=CUR, rule="= Location.currency"),
       C("band_min", "REAL", unit="local currency/yr, FTE=1.0", rule="0 < min < mid"),
       C("band_mid", "REAL", unit="local currency/yr, FTE=1.0", rule="min < mid < max"),
       C("band_max", "REAL", unit="local currency/yr, FTE=1.0", rule="> mid"),
       C("effective_from", "DATE"), C("effective_to", "DATE", rule=">= effective_from"),
       C("version_year", "INTEGER", rule="= year(effective_from)"),
       C("status", "TEXT", allowed=["ACTIVE", "EXPIRED"], rule="ACTIVE iff effective period covers AS_OF date"),
       C("supersedes_band_id", "TEXT", False, fk="CompensationBand.band_id")])
table("Employee", "employees", ["employee_id"], "Employee master record. Pay/position history lives in SalaryRecord (never overwritten).",
      "Employee 1:N SalaryRecord; Employee 1:1 Tenure; Employee 1:N PerformanceEvidence; Employee 1:N Promotion; Employee N:1 Employee (manager, optional)",
      [C("employee_id", "TEXT", uniq=True, rule="^EMP-\\d{6}$"), C("hire_date", "DATE", rule="<= first SalaryRecord.effective_from"),
       C("termination_date", "DATE", False, rule="> hire_date; null iff ACTIVE"),
       C("status", "TEXT", allowed=["ACTIVE", "TERMINATED"]), C("manager_id", "TEXT", False, fk="Employee.employee_id")])
table("Tenure", "tenures", ["tenure_id"], "Tenure derived from hire/termination date as of the snapshot (derived, 1:1 with Employee).",
      "Employee 1:1 Tenure",
      [C("tenure_id", "TEXT", uniq=True, rule="^TEN-\\d{6}$"), C("employee_id", "TEXT", uniq=True, fk="Employee.employee_id"),
       C("as_of_date", "DATE", rule="min(snapshot date, termination_date)"),
       C("tenure_months", "INTEGER", unit="months", rule="whole months hire_date -> as_of_date"),
       C("tenure_years", "REAL", unit="years", rule="(as_of_date-hire_date)/365.25, 2dp"),
       C("tenure_band", "TEXT", allowed=["<1y", "1-3y", "3-5y", "5-10y", "10y+"])])
table("SalaryRecord", "salary_records", ["salary_id"],
      "Effective-dated salary/position event. Every change adds a row; history is never overwritten.",
      "Employee 1:N SalaryRecord; SalaryRecord N:1 Role/Level/Location/Band; SalaryRecord 0..1:1 Promotion; SalaryRecord 0..1:1 AdjustmentProposal",
      [C("salary_id", "TEXT", uniq=True, rule="^SAL-EMP-\\d{6}-\\d{4}-\\d{2}$ i.e. SAL-<employee-id>-<year>-<seq>"),
       C("employee_id", "TEXT", fk="Employee.employee_id"), C("role_id", "TEXT", fk="Role.role_id"),
       C("level_id", "TEXT", fk="Level.level_id"), C("location_id", "TEXT", fk="Location.location_id"),
       C("band_id", "TEXT", fk="CompensationBand.band_id", rule="band for role/level/location effective on effective_from"),
       C("effective_from", "DATE"), C("effective_to", "DATE", False, rule="next record's effective_from - 1 day; null = current"),
       C("currency", "TEXT", allowed=CUR, rule="= Location.currency"),
       C("fte", "REAL", unit="fraction", rule="0.5 <= fte <= 1.0"),
       C("base_salary", "REAL", unit="local currency/yr, actually paid (pro-rated by FTE)", rule="> 0; FTE-equivalent salary = base_salary / fte"),
       C("change_reason", "TEXT", allowed=CHANGE_REASONS),
       C("promotion_id", "TEXT", False, fk="Promotion.promotion_id", rule="required iff PROMOTION"),
       C("adjustment_id", "TEXT", False, fk="AdjustmentProposal.proposal_id", rule="required iff PROPOSAL_ADJUSTMENT")])
table("PerformanceEvidence", "performance_evidence", ["evidence_id"],
      "Documented pay factors: annual review ratings and approved premiums (critical skill, certification).",
      "Employee 1:N PerformanceEvidence",
      [C("evidence_id", "TEXT", uniq=True, rule="^PEV-\\d{6}$"), C("employee_id", "TEXT", fk="Employee.employee_id"),
       C("evidence_type", "TEXT", allowed=["ANNUAL_REVIEW", "CRITICAL_SKILL_PREMIUM", "CERTIFICATION"]),
       C("cycle_year", "INTEGER", False, rule="required iff ANNUAL_REVIEW"),
       C("rating", "INTEGER", False, allowed=[1, 2, 3, 4, 5], rule="required iff ANNUAL_REVIEW"),
       C("pay_factor_pct", "REAL", False, unit="fraction", rule="required iff premium types; 0 < x <= 0.20"),
       C("effective_from", "DATE"), C("recorded_date", "DATE", rule=">= hire_date"), C("document_ref", "TEXT")])
table("Promotion", "promotions", ["promotion_id"], "Level promotion event with the resulting salary record.",
      "Employee 1:N Promotion; Promotion 1:1 SalaryRecord",
      [C("promotion_id", "TEXT", uniq=True, rule="^PRM-\\d{6}$"), C("employee_id", "TEXT", fk="Employee.employee_id"),
       C("role_id", "TEXT", fk="Role.role_id"), C("from_level_id", "TEXT", fk="Level.level_id"),
       C("to_level_id", "TEXT", fk="Level.level_id", rule="level_number = from + 1"),
       C("effective_date", "DATE"), C("pct_increase", "REAL", unit="fraction", rule="0.08..0.15; = new/old FTE-equivalent salary - 1"),
       C("salary_id", "TEXT", uniq=True, fk="SalaryRecord.salary_id")])
table("CompaRatioSnapshot", "compa_ratio_snapshots", ["snapshot_id"],
      "Derived compa-ratio and range position per active employee on the snapshot date. Records the METHOD used (band, FTE, FX).",
      "Employee 1:1 snapshot (per date); SalaryRecord 1:N snapshot; Band 1:N snapshot",
      [C("snapshot_id", "TEXT", uniq=True, rule="^CRS-EMP-\\d{6}-\\d{4}-\\d{2}$"),
       C("snapshot_date", "DATE"), C("employee_id", "TEXT", fk="Employee.employee_id"),
       C("salary_id", "TEXT", fk="SalaryRecord.salary_id", rule="record effective on snapshot_date"),
       C("band_id_used", "TEXT", fk="CompensationBand.band_id", rule="should be effective on snapshot_date"),
       C("salary_currency", "TEXT", allowed=CUR), C("band_currency", "TEXT", allowed=CUR),
       C("fte", "REAL", unit="fraction"), C("fte_applied", "BOOLEAN", rule="salary_used = base/fte if 1 else base"),
       C("fx_applied", "BOOLEAN", rule="if 1, normalized = salary_used * fx_rate_used"),
       C("fx_rate_used", "REAL", False, unit="USD per 1 unit", rule="null iff fx_applied = 0"),
       C("salary_used", "REAL", unit="local currency/yr"), C("normalized_salary_usd", "REAL", unit="USD/yr"),
       C("band_min_usd", "REAL", unit="USD/yr"), C("band_mid_usd", "REAL", unit="USD/yr"), C("band_max_usd", "REAL", unit="USD/yr"),
       C("compa_ratio", "REAL", rule="normalized_salary_usd / band_mid_usd"),
       C("range_position", "REAL", rule="(normalized - band_min) / (band_max - band_min); <0 below band, >1 above")])
table("ComparableGroup", "comparable_groups", ["group_id"],
      "Peer group used for pay comparison. RULE_BASED = same role family + level + location. MANUAL groups need a rationale.",
      "ComparableGroup N:M Employee via ComparableGroupMember",
      [C("group_id", "TEXT", uniq=True, rule="CG-<family>-<level>-<location> or CG-MANUAL-nnnn"),
       C("group_name", "TEXT"), C("grouping_basis", "TEXT", allowed=["RULE_BASED", "MANUAL"]),
       C("role_family", "TEXT", False, allowed=FAMS), C("level_id", "TEXT", False, fk="Level.level_id"),
       C("location_id", "TEXT", False, fk="Location.location_id"),
       C("rationale", "TEXT", False, rule="mandatory when members span >1 role family"),
       C("snapshot_date", "DATE"), C("member_count", "INTEGER", rule="= count of bridge rows"),
       C("min_size_met", "BOOLEAN", rule="member_count >= 5"), C("status", "TEXT", allowed=["ACTIVE"])])
table("ComparableGroupMember", "comparable_group_members", ["group_id", "employee_id"],
      "Bridge table for the N:M relationship Employee <-> ComparableGroup.", "Employee N:M ComparableGroup",
      [C("group_id", "TEXT", fk="ComparableGroup.group_id"), C("employee_id", "TEXT", fk="Employee.employee_id"),
       C("role_id", "TEXT", fk="Role.role_id"), C("level_id", "TEXT", fk="Level.level_id"),
       C("location_id", "TEXT", fk="Location.location_id"), C("joined_date", "DATE")])
table("AdjustmentProposal", "adjustment_proposals", ["proposal_id"],
      "Pay-adjustment proposal raised for an unexplained gap, with evidence and lifecycle state.",
      "Employee 1:N Proposal; Proposal 1:N ApprovalEvent; Proposal 0..1:1 SalaryRecord (when APPLIED)",
      [C("proposal_id", "TEXT", uniq=True, rule="^ADJ-2026-\\d{6}$"), C("employee_id", "TEXT", fk="Employee.employee_id"),
       C("snapshot_id", "TEXT", fk="CompaRatioSnapshot.snapshot_id"), C("salary_id", "TEXT", fk="SalaryRecord.salary_id"),
       C("band_id", "TEXT", fk="CompensationBand.band_id"), C("group_id", "TEXT", fk="ComparableGroup.group_id"),
       C("trigger_type", "TEXT", allowed=["BELOW_EXPECTED", "ABOVE_EXPECTED"]),
       C("residual_z", "REAL", rule="robust z of unexplained gap"), C("currency", "TEXT", allowed=CUR),
       C("current_fte_salary", "REAL", unit="local/yr", rule="base_salary / fte"),
       C("expected_fte_salary", "REAL", unit="local/yr"), C("proposed_fte_salary", "REAL", unit="local/yr"),
       C("fte", "REAL"), C("proposed_base_salary", "REAL", unit="local/yr", rule="round(proposed_fte_salary * fte)"),
       C("adjustment_pct", "REAL", unit="fraction", rule="proposed_fte/current_fte - 1"),
       C("status", "TEXT", allowed=PROPOSAL_STATUSES, rule="= to_status of last ApprovalEvent"),
       C("created_date", "DATE"), C("created_by", "TEXT", fk="Employee.employee_id", rule="HR partner"),
       C("effective_date", "DATE", False, rule="set iff APPLIED"), C("evidence_summary", "TEXT")])
table("ApprovalEvent", "approval_events", ["event_id"],
      "Append-only audit trail: one row per proposal state change.", "AdjustmentProposal 1:N ApprovalEvent",
      [C("event_id", "TEXT", uniq=True, rule="^AEV-\\d{6}$"), C("proposal_id", "TEXT", fk="AdjustmentProposal.proposal_id"),
       C("event_seq", "INTEGER", rule="1..n contiguous per proposal"),
       C("from_status", "TEXT", False, allowed=PROPOSAL_STATUSES, rule="null only for creation"),
       C("to_status", "TEXT", allowed=PROPOSAL_STATUSES, rule="must be a legal transition"),
       C("event_date", "DATE", rule="non-decreasing per proposal"),
       C("actor_role", "TEXT", allowed=["SYSTEM", "HR_PARTNER", "MANAGER", "SYSTEM_ADMIN"]),
       C("actor_id", "TEXT", False, fk="Employee.employee_id", rule="null for SYSTEM / SYSTEM_ADMIN"),
       C("comment", "TEXT", False)])

GROUND_TRUTH_COLUMNS = ["gt_id", "entity_type", "entity_id", "issue_type", "expected_detection_rule",
                        "expected_decision", "context"]
LEAK_COLUMNS = {"issue_type", "ground_truth", "gt_id", "is_anomaly", "expected_decision", "injected"}


def columns(tname):
    return [c[0] for c in SCHEMA[tname]["cols"]]


def by_file():
    return {v["file"]: k for k, v in SCHEMA.items()}
