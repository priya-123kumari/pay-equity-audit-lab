"""Step 1 of the pipeline: master data (Role, Level, Location, FXRate, CompensationBand)."""
from datetime import date
import pandas as pd
from . import reference as R
from .config import AS_OF_DATE


class Master:
    """Holds master tables plus fast lookups used by later stages."""

    def __init__(self):
        self.band = {}            # (role, level, loc, year) -> dict
        self.band_by_id = {}
        self.fx = R.FX            # currency -> year -> rate
        self.loc_cur = {l[0]: l[3] for l in R.LOCATIONS}
        self.role_family = {r[0]: r[2] for r in R.ROLES}

    def rate(self, currency, year):
        return self.fx[currency][year]


def _step(cur):
    return 1000 if cur == "INR" else 100


def build_master():
    M = Master()
    roles = pd.DataFrame([dict(role_id=c, role_name=n, role_family=f, l1_midpoint_usd=float(b), status="ACTIVE")
                          for c, n, f, b, _ in R.ROLES])
    levels = pd.DataFrame([dict(level_id=f"L{n}", level_number=n, level_name=R.LEVEL_NAMES[n - 1],
                                midpoint_multiplier=round(R.LEVEL_STEP ** (n - 1), 4),
                                range_spread_pct=round(0.30 + 0.01 * (n - 1), 2)) for n in range(1, 11)])
    locations = pd.DataFrame([dict(location_id=i, city=c, country=co, currency=cur, col_index=col, status="ACTIVE")
                              for i, c, co, cur, col, _ in R.LOCATIONS])
    fx_rows = []
    for cur in sorted(R.FX):
        for y in R.BAND_YEARS:
            fx_rows.append(dict(fx_id=f"FX-{cur}-{y}", currency=cur, rate_to_usd=R.FX[cur][y],
                                effective_from=date(y, 1, 1).isoformat(), effective_to=date(y, 12, 31).isoformat()))
    fx = pd.DataFrame(fx_rows)

    band_rows = []
    for y in R.BAND_YEARS:
        for code, _, _, base, _ in R.ROLES:
            for n in range(1, 11):
                spread = 0.30 + 0.01 * (n - 1)
                for loc, _, _, cur, col, _ in R.LOCATIONS:
                    mid_usd = base * (R.LEVEL_STEP ** (n - 1)) * col * R.YEAR_FACTOR[y]
                    st = _step(cur)
                    mid = round(mid_usd / R.FX[cur][y] / st) * st
                    lo = round(mid * (1 - spread / 2) / st) * st
                    hi = round(mid * (1 + spread / 2) / st) * st
                    eff_from, eff_to = date(y, 1, 1), date(y, 12, 31)
                    row = dict(band_id=f"BAND-{code}-L{n}-{loc}-{y}", role_id=code, level_id=f"L{n}", location_id=loc,
                               currency=cur, band_min=float(lo), band_mid=float(mid), band_max=float(hi),
                               effective_from=eff_from.isoformat(), effective_to=eff_to.isoformat(), version_year=y,
                               status="ACTIVE" if eff_from <= AS_OF_DATE <= eff_to else "EXPIRED",
                               supersedes_band_id=(f"BAND-{code}-L{n}-{loc}-{y - 1}" if y > R.BAND_YEARS[0] else None))
                    band_rows.append(row)
                    M.band[(code, f"L{n}", loc, y)] = row
                    M.band_by_id[row["band_id"]] = row
    bands = pd.DataFrame(band_rows)
    return M, dict(Role=roles, Level=levels, Location=locations, FXRate=fx, CompensationBand=bands)
