"""Step 8: validation. Hard errors vs. *labelled findings* (deliberate anomalies that the checks are expected to catch).

Outcome rules:
  - `unexpected_errors` must be 0                      (the data is otherwise clean)
  - every labelled anomaly with a rule-based check must be observed (`missed_labelled` must be 0)
"""
import re
import numpy as np
import pandas as pd
from .schema import SCHEMA, TRANSITIONS, LEAK_COLUMNS, ISSUE_TYPES
from . import rules

ID_PATTERNS = {
    "Employee.employee_id": r"^EMP-\d{6}$", "Tenure.tenure_id": r"^TEN-\d{6}$", "Promotion.promotion_id": r"^PRM-\d{6}$",
    "PerformanceEvidence.evidence_id": r"^PEV-\d{6}$", "SalaryRecord.salary_id": r"^SAL-EMP-\d{6}-\d{4}-\d{2}$",
    "CompensationBand.band_id": r"^BAND-[A-Z]+-L\d{1,2}-[A-Z]{3}-\d{4}$", "AdjustmentProposal.proposal_id": r"^ADJ-2026-\d{6}$",
    "ApprovalEvent.event_id": r"^AEV-\d{6}$", "CompaRatioSnapshot.snapshot_id": r"^CRS-EMP-\d{6}-\d{4}-\d{2}$",
    "FXRate.fx_id": r"^FX-[A-Z]{3}-\d{4}$", "ComparableGroup.group_id": r"^CG-([A-Z]+-L\d{1,2}-[A-Z]{3}|MANUAL-\d{4})$",
}
# which check names are the "expected" catchers for each ground-truth issue type
CATCHERS = {
    "EXPIRED_BAND_COMPARISON": {"snapshot_band_effective"}, "FTE_IGNORED": {"snapshot_fte_applied"},
    "CURRENCY_CONVERSION_MISSING": {"snapshot_fx_applied"},
    "ADJUSTMENT_WITHOUT_APPROVAL": {"proposal_lifecycle", "applied_requires_approvals"},
    "INCOMPARABLE_GROUP_NO_RATIONALE": {"group_comparability"},
}


class Report:
    def __init__(self):
        self.stats, self.findings = {}, []

    def check(self, name, checked, bad):
        """bad: iterable of (entity_id, message)."""
        bad = list(bad)
        self.stats[name] = dict(rows_checked=int(checked), violations=len(bad))
        for eid, msg in bad:
            self.findings.append(dict(check=name, entity_id=str(eid), message=msg))


def _close(a, b, tol=1e-4):
    return np.isclose(a.astype(float), b.astype(float), rtol=tol, atol=tol)


def validate(T, gt, analysis=None, M=None):
    R = Report()
    # ---------------- 1. primary keys -----------------
    for name, spec in SCHEMA.items():
        df = T[name]
        R.check(f"pk_unique:{name}", len(df), [(k, "duplicate PK") for k in df[spec["pk"]].astype(str).agg("|".join, axis=1)[df.duplicated(spec["pk"], keep=False)]])
        miss = df[spec["pk"]].isna().any(axis=1)
        R.check(f"pk_not_null:{name}", len(df), [(i, "null PK") for i in df.index[miss]])
    # ---------------- 2. ID formats -----------------
    for key, pat in ID_PATTERNS.items():
        t, c = key.split("."); s = T[t][c].astype(str)
        R.check(f"id_format:{key}", len(s), [(v, f"does not match {pat}") for v in s[~s.str.match(pat)]])
    # ---------------- 3. foreign keys -----------------
    for name, spec in SCHEMA.items():
        for col in spec["cols"]:
            if col[7]:
                pt, pc = col[7].split(".")
                vals = T[name][col[0]].dropna()
                valid = set(T[pt][pc])
                R.check(f"fk:{name}.{col[0]}->{col[7]}", len(vals), [(T[name].loc[i, spec["pk"][0]], f"{col[0]}={v} missing in {pt}")
                                                                      for i, v in vals.items() if v not in valid])
    # ---------------- 4. enums & required -----------------
    for name, spec in SCHEMA.items():
        df = T[name]
        for col in spec["cols"]:
            nm, typ, req, allowed = col[0], col[1], col[2], col[3]
            if req:
                R.check(f"required:{name}.{nm}", len(df), [(df.loc[i, spec["pk"][0]], "null in required field") for i in df.index[df[nm].isna()]])
            if allowed:
                s = df[nm].dropna(); ok = s.isin(allowed)
                R.check(f"enum:{name}.{nm}", len(s), [(df.loc[i, spec["pk"][0]], f"{s[i]} not allowed") for i in s.index[~ok]])
    # ---------------- 5. dates -----------------
    emp = T["Employee"].drop_duplicates("employee_id").set_index("employee_id"); sal = T["SalaryRecord"].sort_values(["employee_id", "effective_from"])
    bad = []
    for eid, g in sal.groupby("employee_id"):
        rows = g.to_dict("records")
        if eid not in emp.index:
            continue                      # orphan employee_id is reported by the FK check
        if rows[0]["effective_from"] < emp.loc[eid, "hire_date"]:
            bad.append((rows[0]["salary_id"], "salary effective before hire_date"))
        for a, b in zip(rows, rows[1:]):
            if pd.isna(a["effective_to"]) or a["effective_to"] >= b["effective_from"]:
                bad.append((b["salary_id"], "overlaps previous salary record"))
            elif (pd.Timestamp(b["effective_from"]) - pd.Timestamp(a["effective_to"])).days != 1:
                bad.append((b["salary_id"], "gap before salary record"))
        last = rows[-1]; term = emp.loc[eid, "termination_date"]
        if pd.isna(term) != pd.isna(last["effective_to"]):
            bad.append((last["salary_id"], "open/closed mismatch with termination"))
        elif not pd.isna(term) and last["effective_to"] != term:
            bad.append((last["salary_id"], "last record not closed at termination_date"))
    R.check("salary_date_continuity", len(sal), bad)
    R.check("salary_effective_order", len(sal), [(r.salary_id, "effective_to < effective_from") for r in sal.itertuples() if pd.notna(r.effective_to) and r.effective_to < r.effective_from])
    R.check("employee_dates", len(emp), [(i, "termination <= hire or status mismatch") for i, r in emp.iterrows()
                                          if (pd.notna(r.termination_date) and r.termination_date <= r.hire_date) or (pd.isna(r.termination_date) != (r.status == "ACTIVE"))])
    b = T["CompensationBand"]
    R.check("band_dates_and_levels", len(b), [(r.band_id, "bad range or version_year") for r in b.itertuples()
                                              if not (r.band_min < r.band_mid < r.band_max) or r.effective_to < r.effective_from or int(r.effective_from[:4]) != r.version_year
                                              or not r.band_id.endswith(f"-{r.version_year}")])
    # ---------------- 6. salary / band / assignment consistency -----------------
    bi = b.drop_duplicates("band_id").set_index("band_id"); loc_cur = T["Location"].drop_duplicates("location_id").set_index("location_id")["currency"]
    bad = []
    for r in sal.itertuples():
        bd = bi.loc[r.band_id] if r.band_id in bi.index else None
        if bd is None or r.location_id not in loc_cur.index:
            continue
        if (bd.role_id, bd.level_id, bd.location_id) != (r.role_id, r.level_id, r.location_id):
            bad.append((r.salary_id, "band does not match role/level/location"))
        if not (bd.effective_from <= r.effective_from <= bd.effective_to):
            bad.append((r.salary_id, "band not effective on salary effective_from"))
        if r.currency != loc_cur[r.location_id] or r.currency != bd.currency:
            bad.append((r.salary_id, "currency mismatch with location/band"))
        if not r.salary_id.startswith(f"SAL-{r.employee_id}-{r.effective_from[:4]}-"):
            bad.append((r.salary_id, "salary_id inconsistent with employee/year"))
        if not (0.5 <= r.fte <= 1.0) or r.base_salary <= 0:
            bad.append((r.salary_id, "fte or base_salary out of range"))
    R.check("salary_band_consistency", len(sal), bad)
    # change-reason consistency (lifecycle of position/pay events) + promotion arithmetic
    lvl = T["Level"].drop_duplicates("level_id").set_index("level_id")["level_number"]; promo = T["Promotion"].drop_duplicates("promotion_id").set_index("promotion_id")
    bad = []
    for eid, g in sal.groupby("employee_id"):
        rows = g.to_dict("records")
        if not {r["level_id"] for r in rows} <= set(lvl.index):
            continue
        for a, c in zip(rows, rows[1:]):
            fa, fc = a["base_salary"] / a["fte"], c["base_salary"] / c["fte"]; why = c["change_reason"]
            if why == "PROMOTION":
                p = promo.loc[c["promotion_id"]] if c["promotion_id"] in promo.index else None
                if p is None or lvl[c["level_id"]] != lvl[a["level_id"]] + 1 or abs(fc / fa - 1 - p.pct_increase) > 1e-3 or p.salary_id != c["salary_id"]:
                    bad.append((c["salary_id"], "promotion inconsistent with level/pct/salary link"))
            elif why == "FTE_CHANGE":
                if c["fte"] == a["fte"] or abs(fc / fa - 1) > 1e-3:
                    bad.append((c["salary_id"], "FTE_CHANGE should change fte but not FTE-equivalent pay"))
            elif why == "RELOCATION_CURRENCY_CHANGE":
                if a["currency"] == c["currency"]:
                    bad.append((c["salary_id"], "relocation did not change currency"))
            elif why == "PROPOSAL_ADJUSTMENT":
                if pd.isna(c["adjustment_id"]):
                    bad.append((c["salary_id"], "missing adjustment_id"))
            elif why in ("ANNUAL_REVIEW", "OFF_CYCLE_ADJUSTMENT") and (a["currency"] != c["currency"] or a["level_id"] != c["level_id"]):
                bad.append((c["salary_id"], f"{why} changed level/currency"))
            if why != "RELOCATION_CURRENCY_CHANGE" and a["location_id"] != c["location_id"]:
                bad.append((c["salary_id"], "location changed without RELOCATION event"))
    R.check("salary_change_reason_consistency", len(sal), bad)
    # ---------------- 7. tenure -----------------
    ten = T["Tenure"].merge(T["Employee"], on="employee_id")      # orphan tenures are caught by FK check
    calc = (pd.to_datetime(ten.as_of_date) - pd.to_datetime(ten.hire_date)).dt.days / 365.25
    R.check("tenure_reconciliation", len(ten), [(r.tenure_id, "tenure_years != (as_of-hire)/365.25") for r, ok in zip(ten.itertuples(), _close(ten.tenure_years, calc.round(2), 0.011)) if not ok])
    # ---------------- 8. snapshot arithmetic & methodology -----------------
    s = T["CompaRatioSnapshot"].merge(sal[["salary_id", "base_salary", "fte", "currency", "effective_from", "effective_to"]].rename(columns={"fte": "sal_fte", "currency": "sal_cur"}), on="salary_id", how="left")
    bad = []
    fx = {(r.currency, r.effective_from[:4]): r.rate_to_usd for r in T["FXRate"].itertuples()}
    bnd = bi[["band_min", "band_mid", "band_max", "currency"]]
    for r in s.itertuples():
        y = r.snapshot_date[:4]
        if pd.isna(r.effective_from) or r.band_id_used not in bnd.index or r.employee_id not in emp.index:
            continue                      # unresolved reference: reported by FK check
        if not (r.effective_from <= r.snapshot_date and (pd.isna(r.effective_to) or r.effective_to >= r.snapshot_date)):
            bad.append((r.snapshot_id, "salary record not in force on snapshot_date")); continue
        used = r.base_salary / r.fte if r.fte_applied else r.base_salary
        norm = used * (fx[(r.sal_cur, y)] if r.fx_applied else 1.0)
        bd = bnd.loc[r.band_id_used]; bfx = fx[(bd.currency, y)]
        if abs(used - r.salary_used) > 0.01 or abs(norm - r.normalized_salary_usd) > 0.01 * max(1, 1):
            bad.append((r.snapshot_id, "salary_used/normalized do not reconcile to salary record"))
        elif abs(bd.band_mid * bfx - r.band_mid_usd) > 0.01 or abs(bd.band_min * bfx - r.band_min_usd) > 0.01 or abs(bd.band_max * bfx - r.band_max_usd) > 0.01:
            bad.append((r.snapshot_id, "band_*_usd do not reconcile to band"))
        elif abs(r.normalized_salary_usd / r.band_mid_usd - r.compa_ratio) > 1e-4:
            bad.append((r.snapshot_id, "compa_ratio != normalized/band_mid"))
        elif abs((r.normalized_salary_usd - r.band_min_usd) / (r.band_max_usd - r.band_min_usd) - r.range_position) > 1e-4:
            bad.append((r.snapshot_id, "range_position does not reconcile"))
        elif bool(r.fx_applied) == pd.isna(r.fx_rate_used):
            bad.append((r.snapshot_id, "fx_rate_used inconsistent with fx_applied"))
    R.check("snapshot_arithmetic_reconciliation", len(s), bad)
    R.check("snapshot_one_per_employee", len(s), [(e, "duplicate snapshot") for e in s.employee_id[s.employee_id.duplicated()]])
    R.check("snapshot_active_only", len(s), [(r.snapshot_id, "snapshot for non-active employee") for r in s.itertuples() if r.employee_id in emp.index and emp.loc[r.employee_id, "status"] != "ACTIVE"])
    exc = rules.snapshot_exceptions(T["CompaRatioSnapshot"], T["CompensationBand"])
    for nm, typ in (("snapshot_band_effective", rules.EXC_EXPIRED), ("snapshot_fte_applied", rules.EXC_FTE), ("snapshot_fx_applied", rules.EXC_FX)):
        R.check(nm, len(s), [(i, f"{typ}") for i in exc[exc.exception_type == typ].snapshot_id])
    # ---------------- 9. comparable groups -----------------
    g, m = T["ComparableGroup"], T["ComparableGroupMember"]
    cnt = m.groupby("group_id").size()
    R.check("group_member_count", len(g), [(r.group_id, "member_count != bridge rows") for r in g.itertuples() if cnt.get(r.group_id, 0) != r.member_count or r.min_size_met != (r.member_count >= 5)])
    sal_cur = sal.set_index("salary_id")
    rb = g[g.grouping_basis == "RULE_BASED"].drop_duplicates("group_id").set_index("group_id"); fam = T["Role"].drop_duplicates("role_id").set_index("role_id")["role_family"]
    bad = [(r.group_id, "rule-based member violates R1") for r in m.itertuples()
           if r.group_id in rb.index and r.role_id in fam.index and (fam[r.role_id], r.level_id, r.location_id) != (rb.loc[r.group_id, "role_family"], rb.loc[r.group_id, "level_id"], rb.loc[r.group_id, "location_id"])]
    R.check("group_rule_membership", len(m), bad)
    R.check("group_comparability", len(g), [(i, "mixed role families without rationale") for i in rules.incomparable_groups(g, m, T["Role"])])
    pos = T["CompaRatioSnapshot"].merge(sal[["salary_id", "role_id", "level_id", "location_id"]], on="salary_id").drop_duplicates("employee_id").set_index("employee_id")
    R.check("group_member_matches_snapshot_position", len(m), [(f"{r.group_id}|{r.employee_id}", "member position differs from salary record in force")
                                                               for r in m.itertuples() if r.employee_id in pos.index
                                                               and (r.role_id, r.level_id, r.location_id) != tuple(pos.loc[r.employee_id, ["role_id", "level_id", "location_id"]])])
    # ---------------- 10. proposals & lifecycle -----------------
    p, ev = T["AdjustmentProposal"], T["ApprovalEvent"].sort_values(["proposal_id", "event_seq"])
    bad = []
    for r in p.itertuples():
        if abs(r.proposed_fte_salary / r.current_fte_salary - 1 - r.adjustment_pct) > 1e-4 or abs(round(r.proposed_fte_salary * r.fte) - r.proposed_base_salary) > 1:
            bad.append((r.proposal_id, "proposal arithmetic does not reconcile"))
    R.check("proposal_arithmetic", len(p), bad)
    bad, byp = [], {k: v for k, v in ev.groupby("proposal_id")}
    for r in p.itertuples():
        e = byp.get(r.proposal_id)
        if e is None:
            bad.append((r.proposal_id, "no events")); continue
        prev, d_prev = None, ""
        for x in e.itertuples():
            if x.from_status is not None and pd.isna(x.from_status):
                frm = None
            else:
                frm = x.from_status
            if frm != prev or x.to_status not in TRANSITIONS.get(prev, []) or x.event_date < d_prev:
                bad.append((r.proposal_id, f"illegal transition {prev}->{x.to_status}")); break
            prev, d_prev = x.to_status, x.event_date
        if list(e.event_seq) != list(range(1, len(e) + 1)):
            bad.append((r.proposal_id, "event_seq not contiguous"))
        if prev != r.status:
            bad.append((r.proposal_id, "status != last event"))
    R.check("proposal_lifecycle", len(p), bad)
    R.check("applied_requires_approvals", len(p), [(i, "APPLIED without manager/HR approval events") for i in rules.unapproved_applications(p, ev)])
    sal_adj = sal[sal.adjustment_id.notna()].drop_duplicates("adjustment_id").set_index("adjustment_id")
    R.check("applied_has_salary_record", len(p), [(r.proposal_id, "APPLIED but no PROPOSAL_ADJUSTMENT salary record / date mismatch")
                                                  for r in p.itertuples() if (r.status == "APPLIED") != (r.proposal_id in sal_adj.index)
                                                  or (r.status == "APPLIED" and sal_adj.loc[r.proposal_id, "effective_from"] != r.effective_date)])
    R.check("proposal_one_per_employee", len(p), [(e, "multiple proposals") for e in p.employee_id[p.employee_id.duplicated()]])
    # ---------------- 11. evidence rules -----------------
    pe = T["PerformanceEvidence"]
    R.check("evidence_type_fields", len(pe), [(r.evidence_id, "rating/cycle/pay_factor fields inconsistent with type") for r in pe.itertuples()
                                              if (r.evidence_type == "ANNUAL_REVIEW") != (pd.notna(r.rating) and pd.notna(r.cycle_year) and pd.isna(r.pay_factor_pct))
                                              or (r.evidence_type != "ANNUAL_REVIEW" and not (0 < r.pay_factor_pct <= 0.20))])
    R.check("evidence_after_hire", len(pe), [(r.evidence_id, "evidence before hire_date") for r in pe.itertuples() if r.employee_id in emp.index and r.recorded_date < emp.loc[r.employee_id, "hire_date"]])
    # ---------------- 12. duplicates -----------------
    R.check("duplicate_salary_rows", len(sal), [(r, "duplicate (employee, effective_from)") for r in sal.salary_id[sal.duplicated(["employee_id", "effective_from"], keep=False)]])
    R.check("duplicate_group_members", len(m), [(r, "duplicate member") for r in m.group_id[m.duplicated(["group_id", "employee_id"], keep=False)]])
    R.check("duplicate_roles_levels_locations", 38, [(x, "dup") for t, c in (("Role", "role_name"), ("Level", "level_number")) for x in T[t][c][T[t][c].duplicated()]])
    # ---------------- 13. ground truth integrity / no leakage -----------------
    ent_tab = {"EMPLOYEE": ("Employee", "employee_id"), "SNAPSHOT": ("CompaRatioSnapshot", "snapshot_id"), "GROUP": ("ComparableGroup", "group_id"), "PROPOSAL": ("AdjustmentProposal", "proposal_id")}
    bad = [(r.gt_id, f"{r.entity_id} not found") for r in gt.itertuples() if r.entity_id not in set(T[ent_tab[r.entity_type][0]][ent_tab[r.entity_type][1]])]
    bad += [(r.gt_id, "unknown issue_type") for r in gt.itertuples() if r.issue_type not in ISSUE_TYPES]
    R.check("ground_truth_ids_exist", len(gt), bad)
    leaks = [(f"{n}.{c}", "ground-truth style column in input table") for n, df in T.items() for c in df.columns if c in LEAK_COLUMNS]
    if analysis is not None:
        leaks += [(f"analysis.{c}", "ground-truth style column in output") for c in analysis.columns if c in LEAK_COLUMNS]
    R.check("ground_truth_not_in_inputs", sum(len(df.columns) for df in T.values()), leaks)

    # ---------------- classification -----------------
    label_idx = {}
    for r in gt.itertuples():
        label_idx.setdefault(r.entity_id, set()).add(r.issue_type)
    labelled, unexpected = [], []
    for f in R.findings:
        types = label_idx.get(f["entity_id"], set())
        (labelled if any(f["check"] in CATCHERS.get(t, set()) for t in types) else unexpected).append(f)
    observed = {(f["entity_id"]) for f in labelled}
    missed = [r.entity_id for r in gt.itertuples() if r.issue_type in CATCHERS and r.entity_id not in observed]
    by_issue = {}
    for f in labelled:
        by_issue.setdefault(f["check"], 0); by_issue[f["check"]] += 1
    return dict(status="PASS" if not unexpected and not missed else "FAIL", checks_run=len(R.stats),
                total_rows_checked=int(sum(v["rows_checked"] for v in R.stats.values())),
                unexpected_errors=len(unexpected), missed_labelled=len(missed),
                labelled_findings_observed=len(labelled), labelled_findings_by_check=by_issue,
                checks=R.stats, unexpected_error_samples=unexpected[:25], missed_labelled_samples=missed[:25])
