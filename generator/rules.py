"""Detection rules. Shared by analysis, validation, evaluation and tests. These NEVER read ground truth."""
import pandas as pd
from .config import REPORTING_CURRENCY

EXC_EXPIRED, EXC_FTE, EXC_FX = "EXPIRED_BAND_COMPARISON", "FTE_IGNORED", "CURRENCY_CONVERSION_MISSING"


def snapshot_exceptions(snap, bands):
    """Methodology exceptions on snapshot rows. Priority: expired band > FTE > FX (one label per row)."""
    b = bands.set_index("band_id")
    eff_to = snap.band_id_used.map(b["effective_to"])
    eff_from = snap.band_id_used.map(b["effective_from"])
    expired = (eff_to < snap.snapshot_date) | (eff_from > snap.snapshot_date)
    fte_ign = (~snap.fte_applied.astype(bool)) & (snap.fte < 1.0)
    fx_missing = (snap.salary_currency != REPORTING_CURRENCY) & (~snap.fx_applied.astype(bool))
    typ = pd.Series(None, index=snap.index, dtype=object)
    typ[fx_missing] = EXC_FX
    typ[fte_ign] = EXC_FTE
    typ[expired] = EXC_EXPIRED
    out = pd.DataFrame(dict(snapshot_id=snap.snapshot_id, exception_type=typ))
    return out[out.exception_type.notna()].reset_index(drop=True)


def unapproved_applications(proposals, events):
    """APPLIED proposals lacking MANAGER_APPROVED and HR_APPROVED events."""
    applied = proposals[proposals.status == "APPLIED"].proposal_id
    got = events.groupby("proposal_id")["to_status"].apply(set)
    need = {"MANAGER_APPROVED", "HR_APPROVED"}
    return sorted(p for p in applied if not need <= got.get(p, set()))


def incomparable_groups(groups, members, roles):
    """Groups whose members span >1 role family but carry no rationale."""
    fam = members.merge(roles[["role_id", "role_family"]], on="role_id").groupby("group_id")["role_family"].nunique()
    g = groups.set_index("group_id")
    bad = [gid for gid, n in fam.items() if n > 1 and (pd.isna(g.loc[gid, "rationale"]) or str(g.loc[gid, "rationale"]).strip() == "")]
    return sorted(bad)
