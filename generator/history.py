"""Step 2: employees and their dependent event history.

Pay is generated from documented factors (band midpoint x rating x tenure x approved premiums x small noise)
so that variation is *explainable*. Deliberate unexplained outliers are separate, labelled OFF_CYCLE events.
Every change is a new SalaryRecord; nothing is overwritten.
"""
from datetime import date, timedelta
import numpy as np
from . import reference as R
from .config import HISTORY_START, HIRE_REF_DATE

MONTH_STARTS = [date(y, m, 1) for y in (2024, 2025, 2026) for m in range(2, 13) if date(y, m, 1) <= date(2026, 6, 1)]
PROMO_PROB = {2024: 0.07, 2025: 0.07, 2026: 0.04}


def _rating_from(v):
    return 1 if v < -1.5 else 2 if v < -0.6 else 3 if v < 0.6 else 4 if v < 1.5 else 5


def _tenure_band(y):
    return "<1y" if y < 1 else "1-3y" if y < 3 else "3-5y" if y < 5 else "5-10y" if y < 10 else "10y+"


def generate_history(rng, cfg, M):
    n = cfg.employees
    roles = [r[0] for r in R.ROLES]
    rw = np.array([r[4] for r in R.ROLES], float); rw /= rw.sum()
    locs = [l[0] for l in R.LOCATIONS]
    lw = np.array([l[5] for l in R.LOCATIONS], float); lw /= lw.sum()

    tenure = np.minimum(rng.exponential(4.2, n), 11.4)
    hires = [HIRE_REF_DATE - timedelta(days=int(t * 365.25)) for t in tenure]
    role_i = rng.choice(len(roles), n, p=rw)
    loc_i = rng.choice(len(locs), n, p=lw)
    fte0 = rng.choice(R.FTE_VALUES, n, p=[0.90, 0.05, 0.02, 0.03])
    ability = rng.normal(0, 1, n)
    noise = rng.normal(0, cfg.pay_noise_sd, n)
    lvl_draw = rng.normal(0, 1.5, n)
    prem_u = rng.random(n)
    prem_pct = rng.uniform(0.08, 0.15, n)
    cert_pct = rng.uniform(0.03, 0.05, n)
    term_u = rng.random(n)
    term_pos = rng.random(n)

    # ---- terminations -------------------------------------------------
    terms = [None] * n
    for i in range(n):
        if hires[i] <= date(2025, 12, 31) and term_u[i] < 0.06:
            lo = max(date(2024, 6, 1), hires[i] + timedelta(days=180)); hi = date(2026, 8, 31)
            if lo < hi:
                terms[i] = lo + timedelta(days=int(term_pos[i] * (hi - lo).days))

    # ---- deliberate unexplained outliers (labelled later via ground truth) --------
    elig = [i for i in range(n) if terms[i] is None and hires[i] < date(2026, 1, 1)]
    k = min(len(elig), cfg.count(cfg.outlier_rate))
    outlier_idx = sorted(rng.choice(elig, k, replace=False).tolist()) if k else []
    outlier = {}
    for i in outlier_idx:
        up = rng.random() < 0.5
        mult = float(rng.uniform(1.22, 1.35)) if up else float(rng.uniform(0.70, 0.80))
        d = date(2026, 7, 15) + timedelta(days=int(rng.integers(0, 60)))
        outlier[i] = (d, round(mult, 4))

    employees, salary, evidence, promotions = [], [], [], []
    tenures = []
    final_level = {}
    counters = dict(pev=0, prm=0)
    outlier_info = {}

    for i in range(n):
        eid = f"EMP-{i + 1:06d}"
        hire, term = hires[i], terms[i]
        role = roles[role_i[i]]
        loc = locs[loc_i[i]]
        fte = float(fte0[i])
        tstart = max(0.0, (HISTORY_START - hire).days / 365.25)
        level = int(np.clip(round(2.0 + 0.4 * min(tstart, 12) + lvl_draw[i]), 1, 10))

        # documented evidence: annual review ratings
        ratings = {}
        for cyc in (2023, 2024, 2025):
            if hire < date(cyc, 10, 1) and (term is None or term > date(cyc, 12, 15)):
                rt = _rating_from(ability[i] + rng.normal(0, 0.35))
                ratings[cyc] = rt
                counters["pev"] += 1
                evidence.append(dict(evidence_id=f"PEV-{counters['pev']:06d}", employee_id=eid, evidence_type="ANNUAL_REVIEW",
                                     cycle_year=cyc, rating=rt, pay_factor_pct=None, effective_from=date(cyc, 12, 15).isoformat(),
                                     recorded_date=date(cyc, 12, 15).isoformat(), document_ref=f"REVIEW-{cyc}-{eid}"))
        premiums = []   # (effective_from, pct)
        for typ, u, pct, lo, hi in (("CRITICAL_SKILL_PREMIUM", prem_u[i], prem_pct[i], 0.0, 0.09),
                                    ("CERTIFICATION", prem_u[i], cert_pct[i], 0.09, 0.14)):
            if lo <= u < hi:
                eff = max(hire, HISTORY_START)
                premiums.append((eff, round(float(pct), 4)))
                counters["pev"] += 1
                evidence.append(dict(evidence_id=f"PEV-{counters['pev']:06d}", employee_id=eid, evidence_type=typ,
                                     cycle_year=None, rating=None, pay_factor_pct=round(float(pct), 4),
                                     effective_from=eff.isoformat(), recorded_date=eff.isoformat(),
                                     document_ref=f"{'CSP' if typ.startswith('CRIT') else 'CERT'}-{eid}"))

        # ---- build the event list ------------------------------------------------
        events = []
        events.append((HISTORY_START, "ANNUAL_REVIEW") if hire < HISTORY_START else (hire, "HIRE"))
        for y in (2025, 2026):
            d = date(y, 1, 1)
            if hire < d and (term is None or term > d):
                events.append((d, "ANNUAL_REVIEW"))
        used = {e[0] for e in events}

        def valid(d):
            return d > hire + timedelta(days=90) and (term is None or d < term - timedelta(days=30)) and d not in used

        for y in (2024, 2025, 2026):
            if rng.random() < PROMO_PROB[y]:
                cand = [d for d in MONTH_STARTS if d.year == y and valid(d)]
                if cand:
                    d = cand[int(rng.integers(0, len(cand)))]; used.add(d); events.append((d, "PROMOTION"))
        if rng.random() < 0.06:
            cand = [d for d in MONTH_STARTS if valid(d)]
            if cand:
                d = cand[int(rng.integers(0, len(cand)))]; used.add(d); events.append((d, "FTE_CHANGE"))
        if rng.random() < 0.025:
            cand = [d for d in MONTH_STARTS if valid(d)]
            if cand:
                d = cand[int(rng.integers(0, len(cand)))]; used.add(d); events.append((d, "RELOCATION_CURRENCY_CHANGE"))
        if i in outlier:
            events.append((outlier[i][0], "OFF_CYCLE_ADJUSTMENT"))
        events.sort(key=lambda e: e[0])

        # ---- replay events -> SalaryRecords --------------------------------------------
        prev_fte_sal = None
        year_seq = {}
        rows = []

        def price(d, role, level, loc):
            cands = [y for y in ratings if y <= d.year - 1]
            rating = ratings[max(cands)] if cands else 3
            ten = max(0.0, (d - hire).days / 365.25)
            prem = sum(p for eff, p in premiums if eff <= d)
            mid = M.band[(role, f"L{level}", loc, d.year)]["band_mid"]
            return mid * float(np.exp(R.RATING_COEF * (rating - 3) + R.TENURE_COEF * min(ten, 15) + noise[i])) * (1 + prem)

        for d, typ in events:
            promo_pct = None
            if typ == "HIRE" or (typ == "ANNUAL_REVIEW" and prev_fte_sal is None):
                fte_sal = price(d, role, level, loc)
            elif typ == "ANNUAL_REVIEW":
                fte_sal = max(prev_fte_sal, price(d, role, level, loc))    # policy: no pay cuts at annual review
            elif typ == "PROMOTION":
                if level >= 10:
                    continue
                promo_pct = round(float(rng.uniform(0.08, 0.15)), 4)
                old_level = level; level += 1
                fte_sal = prev_fte_sal * (1 + promo_pct)
            elif typ == "FTE_CHANGE":
                fte = float(rng.choice([f for f in R.FTE_VALUES if f != fte])); fte_sal = prev_fte_sal
            elif typ == "RELOCATION_CURRENCY_CHANGE":
                cur = M.loc_cur[loc]
                cand = [l for l in locs if M.loc_cur[l] != cur]
                loc = cand[int(rng.integers(0, len(cand)))]
                fte_sal = price(d, role, level, loc)
            else:  # OFF_CYCLE_ADJUSTMENT
                fte_sal = prev_fte_sal * outlier[i][1]
            prev_fte_sal = fte_sal
            year_seq[d.year] = year_seq.get(d.year, 0) + 1
            sid = f"SAL-{eid}-{d.year}-{year_seq[d.year]:02d}"
            band_id = M.band[(role, f"L{level}", loc, d.year)]["band_id"]
            pid = None
            if typ == "PROMOTION":
                counters["prm"] += 1
                pid = f"PRM-{counters['prm']:06d}"
                promotions.append(dict(promotion_id=pid, employee_id=eid, role_id=role, from_level_id=f"L{old_level}",
                                       to_level_id=f"L{level}", effective_date=d.isoformat(), pct_increase=promo_pct, salary_id=sid))
            if typ == "OFF_CYCLE_ADJUSTMENT":
                outlier_info[eid] = dict(salary_id=sid, multiplier=outlier[i][1], date=d.isoformat())
            rows.append(dict(salary_id=sid, employee_id=eid, role_id=role, level_id=f"L{level}", location_id=loc, band_id=band_id,
                             effective_from=d.isoformat(), effective_to=None, currency=M.loc_cur[loc], fte=fte,
                             base_salary=float(round(fte_sal * fte)), change_reason=typ, promotion_id=pid, adjustment_id=None))
        for a, b in zip(rows, rows[1:]):
            a["effective_to"] = (date.fromisoformat(b["effective_from"]) - timedelta(days=1)).isoformat()
        if term is not None and rows:
            rows[-1]["effective_to"] = term.isoformat()
        salary.extend(rows)
        final_level[eid] = level

        employees.append(dict(employee_id=eid, hire_date=hire.isoformat(), termination_date=term.isoformat() if term else None,
                              status="ACTIVE" if term is None else "TERMINATED", manager_id=None))
        end = term if term else date(2026, 10, 1)
        days = (end - hire).days
        months = (end.year - hire.year) * 12 + end.month - hire.month - (1 if end.day < hire.day else 0)
        ty = round(days / 365.25, 2)
        tenures.append(dict(tenure_id=f"TEN-{i + 1:06d}", employee_id=eid, as_of_date=end.isoformat(), tenure_months=months,
                            tenure_years=ty, tenure_band=_tenure_band(days / 365.25)))

    # ---- managers: active employees at L6+ manage lower-level staff --------------------
    last_active = {e["employee_id"]: e for e in employees}
    pool = sorted(e["employee_id"] for e in employees if e["status"] == "ACTIVE" and final_level[e["employee_id"]] >= 6)
    for e in employees:
        lv = final_level[e["employee_id"]]
        cands = [m for m in pool if final_level[m] > lv and m != e["employee_id"]]
        if cands:
            e["manager_id"] = cands[int(rng.integers(0, len(cands)))]
    return dict(employees=employees, salary=salary, evidence=evidence, promotions=promotions,
                tenures=tenures, outlier_info=outlier_info)
