"""Step 4: adjustment proposals with evidence and an append-only approval trail."""
import math
from datetime import date, timedelta
from .config import SNAPSHOT_DATE, AS_OF_DATE

# (status, days after creation, actor_role)  -- SLA offsets are part of the documented rule set
PATH_NORMAL = [("DRAFT", 0, "SYSTEM"), ("SUBMITTED", 1, "HR_PARTNER"), ("MANAGER_APPROVED", 4, "MANAGER"),
               ("HR_APPROVED", 8, "HR_PARTNER"), ("APPLIED", 10, "SYSTEM_ADMIN")]
PATH_REJECT = [("DRAFT", 0, "SYSTEM"), ("SUBMITTED", 1, "HR_PARTNER"), ("REJECTED", 3, "HR_PARTNER")]
CAP = 0.35     # increases above 35% stop at HR_APPROVED (need compensation-committee sign-off)


def _path(pct):
    if pct <= 0:
        return PATH_REJECT        # policy: no pay cuts -> rejected / referred
    if pct > CAP:
        return PATH_NORMAL[:4]
    return PATH_NORMAL


def build_events(proposal_id, created, pct, mgr_id, hr_id, counter, path=None):
    """Create events for every stage whose date is on/before AS_OF_DATE. Returns (events, new_counter, final_status, last_date)."""
    events, prev, last_date = [], None, created
    for status, off, role in (path or _path(pct)):
        d = created + timedelta(days=off)
        if d > AS_OF_DATE:
            break
        counter += 1
        actor = None if role in ("SYSTEM", "SYSTEM_ADMIN") else (mgr_id or hr_id) if role == "MANAGER" else hr_id
        comment = {"DRAFT": "Auto-drafted from unexplained-gap analysis", "SUBMITTED": "Evidence reviewed and submitted",
                   "MANAGER_APPROVED": "Manager confirms no undocumented justification" if mgr_id else "No manager of record; HR delegate approved",
                   "HR_APPROVED": "Within policy limits", "APPLIED": "Applied to payroll via new SalaryRecord",
                   "REJECTED": "Policy: no pay reductions; referred to compensation committee"}[status]
        events.append(dict(event_id=f"AEV-{counter:06d}", proposal_id=proposal_id, event_seq=len(events) + 1,
                           from_status=prev, to_status=status, event_date=d.isoformat(), actor_role=role,
                           actor_id=actor, comment=comment))
        prev, last_date = status, d
    return events, counter, prev, last_date


def build_proposals(rng, analysis, snap_by_id, sal_by_id, emp_by_id, hr_pool):
    flagged = analysis[analysis.flag].sort_values("employee_id")
    proposals, events, ev_counter = [], [], 0
    for n, (_, a) in enumerate(flagged.iterrows(), start=1):
        sn = snap_by_id[a.snapshot_id]; sal = sal_by_id[sn["salary_id"]]
        pid = f"ADJ-2026-{n:06d}"
        cur_fte = sal["base_salary"] / sal["fte"]
        expected = cur_fte * math.exp(-a.residual_log)   # pay explained by documented factors
        proposed = round(expected)
        pct = round(proposed / round(cur_fte, 2) - 1, 4)
        created = SNAPSHOT_DATE + timedelta(days=int(rng.integers(1, 19)))
        hr_id = hr_pool[int(rng.integers(0, len(hr_pool)))]
        mgr = emp_by_id[a.employee_id]["manager_id"]
        evs, ev_counter, status, last = build_events(pid, created, pct, mgr, hr_id, ev_counter)
        evidence = (f"compa={a.compa_ratio:.3f}; expected={a.expected_compa:.3f}; z={a.residual_z:+.1f}; group={a.group_id} "
                    f"(n={int(a.group_size)}); rating={int(a.rating)}; tenure={a.tenure_years:.1f}y; "
                    f"documented premium={a.documented_premium_pct:.0%}; confidence={a.confidence}")
        proposals.append(dict(proposal_id=pid, employee_id=a.employee_id, snapshot_id=a.snapshot_id, salary_id=sal["salary_id"],
                              band_id=sn["band_id_used"], group_id=a.group_id, trigger_type=a.flag_type,
                              residual_z=round(float(a.residual_z), 2), currency=sal["currency"],
                              current_fte_salary=round(cur_fte, 2), expected_fte_salary=round(expected, 2),
                              proposed_fte_salary=float(proposed), fte=sal["fte"],
                              proposed_base_salary=float(round(proposed * sal["fte"])), adjustment_pct=pct, status=status,
                              created_date=created.isoformat(), created_by=hr_id,
                              effective_date=last.isoformat() if status == "APPLIED" else None, evidence_summary=evidence))
        events.extend(evs)
    return proposals, events


def apply_proposals(salary_rows, proposals, M):
    """APPLIED proposals add a NEW SalaryRecord (history is never overwritten)."""
    by_emp = {}
    for r in salary_rows:
        by_emp.setdefault(r["employee_id"], []).append(r)
    new_rows = []
    for p in proposals:
        if p["status"] != "APPLIED":
            continue
        d = date.fromisoformat(p["effective_date"])
        last = max(by_emp[p["employee_id"]], key=lambda r: r["effective_from"])
        last["effective_to"] = (d - timedelta(days=1)).isoformat()
        seq = sum(1 for r in by_emp[p["employee_id"]] if r["effective_from"][:4] == str(d.year)) + 1
        row = dict(last, salary_id=f"SAL-{p['employee_id']}-{d.year}-{seq:02d}", effective_from=d.isoformat(), effective_to=None,
                   base_salary=p["proposed_base_salary"], change_reason="PROPOSAL_ADJUSTMENT", promotion_id=None,
                   adjustment_id=p["proposal_id"],
                   band_id=M.band[(last["role_id"], last["level_id"], last["location_id"], d.year)]["band_id"])
        by_emp[p["employee_id"]].append(row); new_rows.append(row)
    return salary_rows + new_rows
