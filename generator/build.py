"""Orchestrates the whole pipeline. Deterministic: one seeded RNG, no wall-clock, stable ordering."""
import numpy as np
import pandas as pd
from .config import Config, SNAPSHOT_DATE
from .master_data import build_master
from .history import generate_history
from . import analysis as A, anomalies as X, proposals as P, rules
from .schema import SCHEMA, GROUND_TRUTH_COLUMNS, columns


def _df(name, rows):
    return pd.DataFrame(rows, columns=columns(name))


def generate_all(cfg: Config | None = None):
    cfg = cfg or Config()
    rng = np.random.default_rng(cfg.seed)
    gt = []

    # 1. master data first
    M, T = build_master()
    # 2. dependent transactions / events (valid parent IDs by construction)
    H = generate_history(rng, cfg, M)
    employees, salary = H["employees"], H["salary"]
    emp_by_id = {e["employee_id"]: e for e in employees}
    X.outlier_labels(gt, H["outlier_info"])
    # 3. derived values: snapshot of compa-ratio / range position (valid baseline)
    cur_sal = A.current_salary_map(salary)
    snap_rows = A.build_snapshot(salary, employees, M)
    groups, members = A.build_rule_groups(cur_sal, employees, M)
    # 4. inject labelled edge cases on top of the valid baseline (disjoint targets)
    X.inject_snapshot_anomalies(rng, cfg, snap_rows, cur_sal, M, set(H["outlier_info"]), gt)
    X.inject_groups(rng, cfg, groups, members, cur_sal, M, gt)

    T.update(Employee=_df("Employee", employees), Tenure=_df("Tenure", H["tenures"]),
             PerformanceEvidence=_df("PerformanceEvidence", H["evidence"]), Promotion=_df("Promotion", H["promotions"]),
             CompaRatioSnapshot=_df("CompaRatioSnapshot", snap_rows), ComparableGroup=_df("ComparableGroup", groups),
             ComparableGroupMember=_df("ComparableGroupMember", members))
    # 5. analysis: exceptions routed aside, expected pay from documented factors, unexplained gaps flagged
    exc = rules.snapshot_exceptions(T["CompaRatioSnapshot"], T["CompensationBand"])
    analysis = A.run_analysis(T, exc)
    # 6. proposals + approval trail, then labelled "applied without approval" cases
    hr_pool = sorted(s["employee_id"] for s in cur_sal.values() if s["role_id"] == "HRP" and emp_by_id[s["employee_id"]]["status"] == "ACTIVE")
    hr_pool = hr_pool or sorted(cur_sal)[:3]
    snap_by_id = {r["snapshot_id"]: r for r in snap_rows}
    sal_by_id = {r["salary_id"]: r for r in salary}
    proposals, events = P.build_proposals(rng, analysis, snap_by_id, sal_by_id, emp_by_id, hr_pool)
    X.inject_unapproved(rng, cfg, proposals, events, emp_by_id, gt)
    salary = P.apply_proposals(salary, proposals, M)       # APPLIED => new SalaryRecord, never an overwrite
    # 7. final tables
    T["SalaryRecord"] = _df("SalaryRecord", salary)
    T["AdjustmentProposal"] = _df("AdjustmentProposal", proposals)
    T["ApprovalEvent"] = _df("ApprovalEvent", sorted(events, key=lambda e: e["event_id"]))
    ground_truth = pd.DataFrame(gt, columns=GROUND_TRUTH_COLUMNS)
    # stable ordering for reproducibility
    for name, spec in SCHEMA.items():
        T[name] = T[name][columns(name)].sort_values(spec["pk"], kind="mergesort").reset_index(drop=True)
    analysis = analysis.sort_values("snapshot_id").reset_index(drop=True)
    return dict(tables=T, ground_truth=ground_truth, analysis=analysis, master=M, config=cfg)
