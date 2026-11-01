"""Step 3: derived values. Compa-ratio, range position, comparable groups, expected pay and unexplained gap.

All derived values are computed from source rows; nothing here is drawn independently.
"""
from datetime import date
import numpy as np
import pandas as pd
from .config import SNAPSHOT_DATE, MIN_GROUP_SIZE, Z_THRESHOLD, REPORTING_CURRENCY


def compa_metrics(base_salary, fte, salary_fx, band_min, band_mid, band_max, band_fx,
                  fte_applied=True, fx_applied=True):
    """Pure function (unit-tested). Returns dict(salary_used, normalized, band_*_usd, compa_ratio, range_position)."""
    salary_used = base_salary / fte if fte_applied else base_salary
    normalized = salary_used * (salary_fx if fx_applied else 1.0)
    lo, mid, hi = band_min * band_fx, band_mid * band_fx, band_max * band_fx
    return dict(salary_used=salary_used, normalized=normalized, band_min_usd=lo, band_mid_usd=mid, band_max_usd=hi,
                compa_ratio=normalized / mid, range_position=(normalized - lo) / (hi - lo))


def snapshot_row(emp_id, sal, band, M, snap=SNAPSHOT_DATE, fte_applied=True, fx_applied=True):
    y = snap.year
    sfx = M.rate(sal["currency"], y)
    m = compa_metrics(sal["base_salary"], sal["fte"], sfx, band["band_min"], band["band_mid"], band["band_max"],
                      M.rate(band["currency"], y), fte_applied, fx_applied)
    return dict(snapshot_id=f"CRS-{emp_id}-{snap.year}-{snap.month:02d}", snapshot_date=snap.isoformat(), employee_id=emp_id,
                salary_id=sal["salary_id"], band_id_used=band["band_id"], salary_currency=sal["currency"],
                band_currency=band["currency"], fte=sal["fte"], fte_applied=fte_applied, fx_applied=fx_applied,
                fx_rate_used=sfx if fx_applied else None, salary_used=round(m["salary_used"], 2),
                normalized_salary_usd=round(m["normalized"], 2), band_min_usd=round(m["band_min_usd"], 2),
                band_mid_usd=round(m["band_mid_usd"], 2), band_max_usd=round(m["band_max_usd"], 2),
                compa_ratio=round(m["compa_ratio"], 4), range_position=round(m["range_position"], 4))


def current_salary_map(salary_rows, snap=SNAPSHOT_DATE):
    """Salary record in force on the snapshot date for each employee (effective-dated lookup)."""
    s = snap.isoformat(); cur = {}
    for r in salary_rows:
        if r["effective_from"] <= s and (r["effective_to"] is None or r["effective_to"] >= s):
            cur[r["employee_id"]] = r
    return cur


def build_snapshot(salary_rows, employees, M):
    cur = current_salary_map(salary_rows)
    rows = []
    for e in employees:
        if e["status"] != "ACTIVE":
            continue
        sal = cur[e["employee_id"]]
        yr = int(sal["effective_from"][:4])
        band = M.band_by_id[sal["band_id"]]
        # the band applicable on the snapshot date (current-year version)
        band = M.band[(sal["role_id"], sal["level_id"], sal["location_id"], SNAPSHOT_DATE.year)]
        rows.append(snapshot_row(e["employee_id"], sal, band, M))
    return rows


def build_rule_groups(cur_sal, employees, M):
    """Rule R1: comparable = same role family + level + location. Returns (group rows, member rows)."""
    buckets = {}
    for e in employees:
        if e["status"] != "ACTIVE":
            continue
        s = cur_sal[e["employee_id"]]
        key = (M.role_family[s["role_id"]], s["level_id"], s["location_id"])
        buckets.setdefault(key, []).append((e["employee_id"], s))
    groups, members = [], []
    for (fam, lvl, loc), mem in sorted(buckets.items(), key=lambda kv: (kv[0][0], int(kv[0][1][1:]), kv[0][2])):
        gid = f"CG-{fam}-{lvl}-{loc}"
        groups.append(dict(group_id=gid, group_name=f"{fam} {lvl} {loc}", grouping_basis="RULE_BASED", role_family=fam,
                           level_id=lvl, location_id=loc,
                           rationale="Rule R1: same role family, level and location",
                           snapshot_date=SNAPSHOT_DATE.isoformat(), member_count=len(mem),
                           min_size_met=len(mem) >= MIN_GROUP_SIZE, status="ACTIVE"))
        for eid, s in sorted(mem):
            members.append(dict(group_id=gid, employee_id=eid, role_id=s["role_id"], level_id=s["level_id"],
                                location_id=s["location_id"], joined_date=SNAPSHOT_DATE.isoformat()))
    return groups, members


def run_analysis(T, exceptions, z_threshold=Z_THRESHOLD):
    """Expected pay from documented factors -> unexplained gap -> flags.

    T: dict of DataFrames keyed by schema table name. exceptions: DataFrame(snapshot_id, exception_type)
    Rows with a methodology exception are routed to an exception queue and excluded from the model.
    """
    snap = T["CompaRatioSnapshot"].copy()
    ev = T["PerformanceEvidence"]; ten = T["Tenure"].set_index("employee_id")["tenure_years"]
    rev = ev[ev.evidence_type == "ANNUAL_REVIEW"].sort_values(["employee_id", "cycle_year"]).groupby("employee_id").tail(1)
    rating = rev.set_index("employee_id")["rating"]
    prem = ev[ev.evidence_type != "ANNUAL_REVIEW"].groupby("employee_id")["pay_factor_pct"].sum()
    snap["rating"] = snap.employee_id.map(rating).fillna(3).astype(float)
    snap["tenure_years"] = snap.employee_id.map(ten).astype(float)
    snap["documented_premium_pct"] = snap.employee_id.map(prem).fillna(0.0).astype(float)
    exc = exceptions.set_index("snapshot_id")["exception_type"] if len(exceptions) else pd.Series(dtype=str)
    snap["exception_type"] = snap.snapshot_id.map(exc)
    snap["analysis_status"] = np.where(snap.exception_type.isna(), "OK", "EXCEPTION")

    mem = T["ComparableGroupMember"].merge(T["ComparableGroup"][["group_id", "grouping_basis", "member_count"]], on="group_id")
    primary = mem[mem.grouping_basis == "RULE_BASED"].set_index("employee_id")[["group_id", "member_count"]]
    snap["group_id"] = snap.employee_id.map(primary["group_id"])
    snap["group_size"] = snap.employee_id.map(primary["member_count"])
    ok = snap.analysis_status == "OK"
    snap["y"] = np.log(snap.compa_ratio.where(snap.compa_ratio > 0))
    X = np.column_stack([np.ones(len(snap)), snap.rating - 3, np.minimum(snap.tenure_years, 15), np.log1p(snap.documented_premium_pct)])
    y = snap.y.to_numpy()
    mask = ok.to_numpy().copy()
    beta = np.zeros(4); sigma = 1.0
    for _ in range(4):                                     # robust re-weighting: drop |z|>3 and refit
        beta, *_ = np.linalg.lstsq(X[mask], y[mask], rcond=None)
        res = y - X @ beta
        sigma = 1.4826 * np.median(np.abs(res[mask] - np.median(res[mask])))
        mask = ok.to_numpy() & (np.abs((res - np.median(res[mask])) / sigma) < 3.0)
    res = y - X @ beta
    z = (res - np.median(res[mask])) / sigma
    snap["expected_compa"] = np.exp(X @ beta)
    snap["residual_log"] = res
    snap["residual_z"] = np.where(ok, z, np.nan)
    gmed = snap[ok].groupby("group_id")["compa_ratio"].median()
    snap["group_median_compa"] = snap.group_id.map(gmed)
    snap["band_position_status"] = np.where(snap.range_position < 0, "BELOW_MIN", np.where(snap.range_position > 1, "ABOVE_MAX", "IN_BAND"))
    flag = ok & (snap.residual_z.abs() > z_threshold)
    snap["flag"] = flag
    snap["flag_type"] = np.where(flag, np.where(snap.residual_z > 0, "ABOVE_EXPECTED", "BELOW_EXPECTED"), None)
    snap["confidence"] = np.where(~flag, None, np.where(snap.group_size >= MIN_GROUP_SIZE, "HIGH", "LOW"))
    cols = ["snapshot_id", "employee_id", "group_id", "group_size", "analysis_status", "exception_type", "rating", "tenure_years",
            "documented_premium_pct", "compa_ratio", "expected_compa", "residual_log", "residual_z", "group_median_compa",
            "band_position_status", "flag", "flag_type", "confidence"]
    out = snap[cols].copy()
    for c in ("expected_compa", "residual_log", "residual_z", "group_median_compa"):
        out[c] = out[c].round(4)
    out.attrs["model"] = dict(intercept=float(beta[0]), rating_coef=float(beta[1]), tenure_coef=float(beta[2]),
                              premium_coef=float(beta[3]), robust_sigma=float(sigma), z_threshold=z_threshold)
    return out
