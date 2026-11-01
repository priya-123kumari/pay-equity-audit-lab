import json, os, re, sqlite3, tempfile
import numpy as np
import pandas as pd
from helpers import dataset, clone_tables
from generator import analysis as A, rules
from generator.__main__ import main
from generator.build import generate_all
from generator.config import Config, SNAPSHOT_DATE
from generator.evaluate import detection_metrics
from generator.export import ddl, seed_sql, _prep
from generator.schema import SCHEMA, LEAK_COLUMNS
from generator.validate import validate, ID_PATTERNS


# ---------- IDs ----------
def test_id_formats_match_spec():
    T = dataset()["tables"]
    for key, pat in ID_PATTERNS.items():
        t, c = key.split(".")
        assert T[t][c].astype(str).str.match(pat).all(), key
    assert T["Employee"].employee_id.iloc[0] == "EMP-000001"
    assert T["AdjustmentProposal"].proposal_id.iloc[0] == "ADJ-2026-000001"
    s = T["SalaryRecord"]
    assert s[s.salary_id == f"SAL-EMP-000001-2026-01"].shape[0] <= 1
    assert s.salary_id.str.match(r"^SAL-EMP-\d{6}-20(24|25|26)-\d{2}$").all()
    assert T["CompensationBand"].band_id.str.match(r"^BAND-[A-Z]+-L\d+-[A-Z]{3}-2026$|^BAND-[A-Z]+-L\d+-[A-Z]{3}-202[45]$").all()


# ---------- reproducibility ----------
def test_same_seed_identical_and_different_seed_differs():
    a = generate_all(Config(employees=120)); b = generate_all(Config(employees=120))
    for k in a["tables"]:
        pd.testing.assert_frame_equal(a["tables"][k], b["tables"][k])
    pd.testing.assert_frame_equal(a["ground_truth"], b["ground_truth"])
    c = generate_all(Config(employees=120, seed=1))
    assert not a["tables"]["SalaryRecord"].base_salary.equals(c["tables"]["SalaryRecord"].base_salary)


def test_cli_checksums_identical_across_runs():
    with tempfile.TemporaryDirectory() as d:
        main(["--employees", "80", "--out", f"{d}/a", "--quiet"]); main(["--employees", "80", "--out", f"{d}/b", "--quiet"])
        ca = json.load(open(f"{d}/a/checksums.json")); cb = json.load(open(f"{d}/b/checksums.json"))
        assert ca == cb and len(ca) >= 30


# ---------- derived-value math ----------
def test_compa_ratio_and_range_position_known_inputs():
    m = A.compa_metrics(base_salary=60000, fte=0.5, salary_fx=1, band_min=90000, band_mid=100000, band_max=110000, band_fx=1)
    assert m["salary_used"] == 120000 and abs(m["compa_ratio"] - 1.2) < 1e-9 and abs(m["range_position"] - 1.5) < 1e-9
    # FTE ignored gives the wrong (low) answer -> exactly what the edge case labels
    w = A.compa_metrics(60000, 0.5, 1, 90000, 100000, 110000, 1, fte_applied=False)
    assert abs(w["compa_ratio"] - 0.6) < 1e-9
    # currency: INR 1,000,000 at 0.0112 = USD 11,200 vs USD band mid 10,000
    c = A.compa_metrics(1_000_000, 1.0, 0.0112, 8000, 10000, 12000, 1)
    assert abs(c["compa_ratio"] - 1.12) < 1e-9 and abs(c["range_position"] - 0.8) < 1e-9
    # conversion missing: INR number compared against USD band
    bad = A.compa_metrics(1_000_000, 1.0, 0.0112, 8000, 10000, 12000, 1, fx_applied=False)
    assert bad["compa_ratio"] == 100.0


def test_snapshot_recomputes_from_sources():
    T = dataset()["tables"]; v = validate(T, dataset()["ground_truth"])
    assert v["checks"]["snapshot_arithmetic_reconciliation"]["violations"] == 0


# ---------- effective-dated bands ----------
def test_bands_are_effective_dated_and_expired_versions_exist():
    T = dataset()["tables"]; b = T["CompensationBand"]
    assert set(b.status) == {"ACTIVE", "EXPIRED"} and set(b.version_year) == {2024, 2025, 2026}
    assert (b[b.version_year == 2026].status == "ACTIVE").all() and (b[b.version_year < 2026].status == "EXPIRED").all()
    assert b.groupby(["role_id", "level_id"]).ngroups == 200              # 200 role/level combinations
    sal = T["SalaryRecord"].merge(b, on="band_id", suffixes=("", "_b"))
    assert ((sal.effective_from >= sal.effective_from_b) & (sal.effective_from <= sal.effective_to_b)).all()
    snap = T["CompaRatioSnapshot"]; exc = set(rules.snapshot_exceptions(snap, b).snapshot_id)
    ok = snap[~snap.snapshot_id.isin(exc)].merge(b, left_on="band_id_used", right_on="band_id")
    assert (ok.status == "ACTIVE").all()


# ---------- every injected anomaly is detectable by rules ----------
def test_injected_anomalies_are_detected_by_rules():
    R = dataset(); m = detection_metrics(R["tables"], R["analysis"], R["ground_truth"])
    for typ in ("EXPIRED_BAND_COMPARISON", "FTE_IGNORED", "CURRENCY_CONVERSION_MISSING", "ADJUSTMENT_WITHOUT_APPROVAL", "INCOMPARABLE_GROUP_NO_RATIONALE"):
        assert m[typ]["ground_truth"] >= 1, typ
        assert m[typ]["recall"] == 1.0 and m[typ]["precision"] == 1.0, (typ, m[typ])
    o = m["UNEXPLAINED_OUTLIER"]
    assert o["ground_truth"] >= 1 and o["recall"] >= 0.95 and o["precision"] >= 0.8, o


def test_anomalies_are_a_small_fraction_and_targets_are_disjoint():
    R = dataset(); gt = R["ground_truth"]
    snap_gt = gt[gt.entity_type == "SNAPSHOT"].entity_id
    assert snap_gt.is_unique and len(snap_gt) < 0.10 * len(R["tables"]["CompaRatioSnapshot"])
    emp_of = lambda s: s[4:14]
    outl = set(gt[gt.issue_type == "UNEXPLAINED_OUTLIER"].entity_id)
    assert not (outl & {emp_of(s) for s in snap_gt})


def test_valid_manual_group_with_rationale_is_not_flagged():
    T = dataset()["tables"]; g = T["ComparableGroup"]
    ok = g[(g.grouping_basis == "MANUAL") & g.rationale.notna()]
    assert len(ok) >= 1 and not (set(ok.group_id) & set(rules.incomparable_groups(g, T["ComparableGroupMember"], T["Role"])))


# ---------- validation ----------
def test_validation_passes_on_generated_data():
    R = dataset(); v = validate(R["tables"], R["ground_truth"], R["analysis"], R["master"])
    assert v["status"] == "PASS" and v["unexpected_errors"] == 0 and v["missed_labelled"] == 0
    assert v["labelled_findings_observed"] >= 5


def _errors(T, gt):
    return validate(T, gt)["unexpected_errors"]


def test_validation_catches_broken_rows():
    R = dataset(); gt = R["ground_truth"]
    base = _errors(R["tables"], gt); assert base == 0
    T = clone_tables(R); T["SalaryRecord"].loc[3, "employee_id"] = "EMP-999999"; assert _errors(T, gt) > 0            # FK
    T = clone_tables(R); T["Employee"].loc[0, "status"] = "FIRED"; assert _errors(T, gt) > 0                         # enum
    T = clone_tables(R); T["CompaRatioSnapshot"].loc[5, "compa_ratio"] += 0.5; assert _errors(T, gt) > 0             # arithmetic
    T = clone_tables(R); T["SalaryRecord"].loc[7, "effective_from"] = "2001-01-01"; assert _errors(T, gt) > 0        # dates
    T = clone_tables(R); T["Employee"].loc[1, "employee_id"] = T["Employee"].loc[2, "employee_id"]; assert _errors(T, gt) > 0  # PK dup
    T = clone_tables(R); T["Tenure"].loc[4, "tenure_years"] += 3; assert _errors(T, gt) > 0                          # derived value
    # lifecycle: remove approvals from a legitimately APPLIED proposal that is NOT in ground truth
    p = T = clone_tables(R); ev = T["ApprovalEvent"]; bad_ids = set(gt[gt.issue_type == "ADJUSTMENT_WITHOUT_APPROVAL"].entity_id)
    legit = T["AdjustmentProposal"][(T["AdjustmentProposal"].status == "APPLIED") & (~T["AdjustmentProposal"].proposal_id.isin(bad_ids))]
    if len(legit):
        pid = legit.proposal_id.iloc[0]
        T["ApprovalEvent"] = ev[~((ev.proposal_id == pid) & (ev.to_status == "HR_APPROVED"))]
        assert _errors(T, gt) > 0
    # an un-labelled methodology exception must be an error, not silently accepted
    T = clone_tables(R); cs = T["CompaRatioSnapshot"]
    idx = cs.index[(cs.salary_currency != "USD") & (~cs.snapshot_id.isin(set(gt.entity_id)))][0]
    cs.loc[idx, "fx_applied"] = False; cs.loc[idx, "fx_rate_used"] = np.nan
    assert _errors(T, gt) > 0


def test_ground_truth_separate_and_not_leaked():
    R = dataset(); gt = R["ground_truth"]
    for n, df in R["tables"].items():
        assert not (set(df.columns) & LEAK_COLUMNS), n
    assert not (set(R["analysis"].columns) & LEAK_COLUMNS)
    assert set(gt.issue_type) == set(__import__("generator.schema", fromlist=["x"]).ISSUE_TYPES)
    assert gt.gt_id.is_unique


# ---------- lifecycle / history ----------
def test_history_is_never_overwritten_applied_proposals_add_records():
    T = dataset()["tables"]; sal = T["SalaryRecord"]; p = T["AdjustmentProposal"]
    applied = p[p.status == "APPLIED"]; assert len(applied) >= 1
    for r in applied.itertuples():
        e = sal[sal.employee_id == r.employee_id].sort_values("effective_from")
        new = e[e.adjustment_id == r.proposal_id].iloc[0]
        prev = e[e.effective_from < new.effective_from].iloc[-1]
        assert prev.salary_id == r.salary_id and prev.effective_to == (pd.Timestamp(new.effective_from) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        assert new.base_salary == r.proposed_base_salary


def test_coverage_of_normal_boundary_and_failure_cases():
    R = dataset(); T = R["tables"]; s = T["SalaryRecord"]
    assert {"HIRE", "ANNUAL_REVIEW", "PROMOTION", "FTE_CHANGE", "RELOCATION_CURRENCY_CHANGE", "OFF_CYCLE_ADJUSTMENT"} <= set(dataset(1500)["tables"]["SalaryRecord"].change_reason)
    assert s.fte.nunique() >= 2 and s.currency.nunique() >= 4
    assert (~T["ComparableGroup"].min_size_met).any() and T["ComparableGroup"].min_size_met.any()      # boundary: size < 5
    assert set(T["AdjustmentProposal"].status) >= {"REJECTED"}                                           # exception path: no pay cuts
    assert T["Employee"].status.nunique() == 2


def test_documented_factors_explain_pay():
    R = dataset(); m = R["analysis"].attrs["model"]
    assert 0.03 < m["rating_coef"] < 0.07 and 0.005 < m["tenure_coef"] < 0.02 and 0.8 < m["premium_coef"] < 1.2


def test_realistic_distributions():
    R = dataset(1500); s = R["tables"]["CompaRatioSnapshot"]; a = R["analysis"]
    c = s[s.snapshot_id.isin(a[a.analysis_status == "OK"].snapshot_id)].compa_ratio
    assert 0.9 < c.median() < 1.2 and 0.02 < c.std() < 0.2
    lv = R["tables"]["SalaryRecord"].drop_duplicates("employee_id", keep="last").level_id.value_counts()
    assert lv.get("L9", 0) + lv.get("L10", 0) < 0.05 * 1500 and lv.max() > lv.get("L9", 0) * 3


# ---------- SQL ----------
def test_sql_seed_loads_with_foreign_keys_enforced():
    T = dataset(120)["tables"]; P = {n: _prep(n, T[n]) for n in SCHEMA}
    c = sqlite3.connect(":memory:"); c.executescript(ddl()); c.executescript(seed_sql(P))
    assert c.execute("PRAGMA foreign_key_check").fetchall() == []
    assert c.execute("select count(*) from employees").fetchone()[0] == 120


def test_scale_is_parameterised():
    for n in (40, 150):
        R = generate_all(Config(employees=n)); assert len(R["tables"]["Employee"]) == n
        assert validate(R["tables"], R["ground_truth"], R["analysis"])["status"] == "PASS"
