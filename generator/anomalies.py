"""Step 5: inject LABELLED edge cases into otherwise-valid data. Targets are disjoint so each label is unambiguous."""
from datetime import date, timedelta
import numpy as np
from .analysis import snapshot_row
from .config import SNAPSHOT_DATE, AS_OF_DATE, MIN_GROUP_SIZE
from . import proposals as P


def _gt(rows, etype, eid, issue, rule, decision, ctx):
    rows.append(dict(gt_id=f"GT-{len(rows) + 1:05d}", entity_type=etype, entity_id=eid, issue_type=issue,
                     expected_detection_rule=rule, expected_decision=decision, context=ctx))


def outlier_labels(gt, outlier_info):
    for eid, o in sorted(outlier_info.items()):
        up = o["multiplier"] > 1
        _gt(gt, "EMPLOYEE", eid, "UNEXPLAINED_OUTLIER",
            "|robust z| of residual after rating/tenure/premium model > threshold, no documented evidence",
            "REFER_TO_COMPENSATION_COMMITTEE" if up else "CREATE_ADJUSTMENT_PROPOSAL",
            f"off-cycle change x{o['multiplier']} on {o['date']} ({o['salary_id']}) without documented factor")


def inject_snapshot_anomalies(rng, cfg, snap_rows, cur_sal, M, exclude_ids, gt):
    by_emp = {r["employee_id"]: i for i, r in enumerate(snap_rows)}
    used = set(exclude_ids)

    def pick(pool, k):
        pool = sorted(e for e in pool if e not in used)
        k = min(k, len(pool))
        chosen = sorted(rng.choice(pool, k, replace=False).tolist()) if k else []
        used.update(chosen)
        return chosen

    y = SNAPSHOT_DATE.year
    allp = list(by_emp)
    for eid in pick(allp, cfg.count(cfg.expired_band_rate)):
        s = cur_sal[eid]; old = M.band[(s["role_id"], s["level_id"], s["location_id"], y - 1)]
        snap_rows[by_emp[eid]] = snapshot_row(eid, s, old, M)
        _gt(gt, "SNAPSHOT", snap_rows[by_emp[eid]]["snapshot_id"], "EXPIRED_BAND_COMPARISON",
            "band_id_used.effective_to < snapshot_date", "RECOMPUTE_WITH_CURRENT_BAND", f"compared against {old['band_id']}")
    for eid in pick([e for e in allp if cur_sal[e]["fte"] < 1.0], cfg.count(cfg.fte_ignored_rate)):
        s = cur_sal[eid]; band = M.band[(s["role_id"], s["level_id"], s["location_id"], y)]
        snap_rows[by_emp[eid]] = snapshot_row(eid, s, band, M, fte_applied=False)
        _gt(gt, "SNAPSHOT", snap_rows[by_emp[eid]]["snapshot_id"], "FTE_IGNORED",
            "fte_applied = 0 and fte < 1", "RECOMPUTE_WITH_FTE_NORMALIZATION", f"raw part-time pay used (fte={s['fte']})")
    for eid in pick([e for e in allp if cur_sal[e]["currency"] != "USD"], cfg.count(cfg.currency_missing_rate)):
        s = cur_sal[eid]; usd = M.band[(s["role_id"], s["level_id"], "NYC", y)]
        snap_rows[by_emp[eid]] = snapshot_row(eid, s, usd, M, fx_applied=False)
        _gt(gt, "SNAPSHOT", snap_rows[by_emp[eid]]["snapshot_id"], "CURRENCY_CONVERSION_MISSING",
            "salary_currency != USD and fx_applied = 0", "RECOMPUTE_WITH_FX_CONVERSION",
            f"{s['currency']} salary compared against USD band {usd['band_id']}")
    return used


def inject_groups(rng, cfg, groups, members, cur_sal, M, gt):
    """Add MANUAL cross-family groups: some with no rationale (anomaly), some with a documented rationale (valid control)."""
    fam_emps = {}
    for eid, s in sorted(cur_sal.items()):
        fam_emps.setdefault(M.role_family[s["role_id"]], []).append(eid)
    fams = sorted(f for f, v in fam_emps.items() if len(v) >= 4)
    if len(fams) < 2:
        return
    n_bad = cfg.count(cfg.incomparable_group_rate)
    n_ok = max(1, n_bad // 3)
    for n in range(1, n_bad + n_ok + 1):
        bad = n <= n_bad
        pair = sorted(rng.choice(len(fams), 2, replace=False).tolist())
        mem = []
        for fi in pair:
            pool = fam_emps[fams[fi]]
            mem += sorted(rng.choice(pool, min(len(pool), int(rng.integers(3, 6))), replace=False).tolist())
        gid = f"CG-MANUAL-{n:04d}"
        names = " + ".join(fams[i] for i in pair)
        groups.append(dict(group_id=gid, group_name=f"Manual cross-family group {names}", grouping_basis="MANUAL",
                           role_family=None, level_id=None, location_id=None,
                           rationale=None if bad else f"Approved by HR: {names} roles share one job-architecture band for this review",
                           snapshot_date=SNAPSHOT_DATE.isoformat(), member_count=len(mem),
                           min_size_met=len(mem) >= MIN_GROUP_SIZE, status="ACTIVE"))
        for eid in mem:
            s = cur_sal[eid]
            members.append(dict(group_id=gid, employee_id=eid, role_id=s["role_id"], level_id=s["level_id"],
                                location_id=s["location_id"], joined_date=SNAPSHOT_DATE.isoformat()))
        if bad:
            _gt(gt, "GROUP", gid, "INCOMPARABLE_GROUP_NO_RATIONALE", "group spans >1 role family and rationale is null",
                "DISSOLVE_OR_DOCUMENT_RATIONALE", f"mixed families {names}, no rationale")


def inject_unapproved(rng, cfg, proposals, events, emp_by_id, gt):
    """Flip some proposals to APPLIED while skipping the manager/HR approval events."""
    cand = sorted(p["proposal_id"] for p in proposals if p["adjustment_pct"] > 0 and p["status"] in ("DRAFT", "SUBMITTED", "MANAGER_APPROVED", "HR_APPROVED"))
    if not cand:
        return
    k = min(len(cand), max(1, int(np.ceil(cfg.unapproved_share * len(proposals)))))
    chosen = sorted(rng.choice(cand, k, replace=False).tolist())
    by_id = {p["proposal_id"]: p for p in proposals}
    counter = max(int(e["event_id"][4:]) for e in events)
    for pid in chosen:
        p = by_id[pid]
        old = [e for e in events if e["proposal_id"] == pid]
        keep = [e for e in old if e["to_status"] in ("DRAFT", "SUBMITTED")]
        keep_ids = {e["event_id"] for e in keep}
        events[:] = [e for e in events if e["proposal_id"] != pid or e["event_id"] in keep_ids]
        d = min(date.fromisoformat(p["created_date"]) + timedelta(days=3), AS_OF_DATE)
        last = keep[-1] if keep else None
        d = max(d, date.fromisoformat(last["event_date"])) if last else d
        counter += 1
        events.append(dict(event_id=f"AEV-{counter:06d}", proposal_id=pid, event_seq=len(keep) + 1,
                           from_status=last["to_status"] if last else None, to_status="APPLIED", event_date=d.isoformat(),
                           actor_role="SYSTEM_ADMIN", actor_id=None, comment="Applied to payroll"))
        p["status"] = "APPLIED"; p["effective_date"] = d.isoformat()
        _gt(gt, "PROPOSAL", pid, "ADJUSTMENT_WITHOUT_APPROVAL", "status = APPLIED and no MANAGER_APPROVED/HR_APPROVED events",
            "REVERSE_AND_ESCALATE_TO_AUDIT", "approval stages skipped before payroll application")
