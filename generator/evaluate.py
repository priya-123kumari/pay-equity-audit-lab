"""Evaluation metrics: (1) detection quality of the rules against ground truth, (2) data-realism statistics."""
import numpy as np
import pandas as pd
from . import rules
from .schema import ISSUE_TYPES


def detections(T, analysis):
    det = {}
    exc = rules.snapshot_exceptions(T["CompaRatioSnapshot"], T["CompensationBand"])
    for typ in (rules.EXC_EXPIRED, rules.EXC_FTE, rules.EXC_FX):
        det[typ] = set(exc[exc.exception_type == typ].snapshot_id)
    det["ADJUSTMENT_WITHOUT_APPROVAL"] = set(rules.unapproved_applications(T["AdjustmentProposal"], T["ApprovalEvent"]))
    det["INCOMPARABLE_GROUP_NO_RATIONALE"] = set(rules.incomparable_groups(T["ComparableGroup"], T["ComparableGroupMember"], T["Role"]))
    det["UNEXPLAINED_OUTLIER"] = set(analysis[analysis.flag].employee_id)
    return det


def detection_metrics(T, analysis, gt):
    det = detections(T, analysis); out = {}
    for typ in ISSUE_TYPES:
        truth = set(gt[gt.issue_type == typ].entity_id); d = det.get(typ, set())
        tp, fp, fn = len(truth & d), len(d - truth), len(truth - d)
        out[typ] = dict(ground_truth=len(truth), detected=len(d), true_positive=tp, false_positive=fp, false_negative=fn,
                        precision=round(tp / (tp + fp), 4) if tp + fp else None, recall=round(tp / (tp + fn), 4) if tp + fn else None)
    return out


def distribution_metrics(T, analysis):
    s = T["CompaRatioSnapshot"]; a = analysis; clean = a[a.analysis_status == "OK"]
    ok_s = s[s.snapshot_id.isin(clean.snapshot_id)]
    sal = T["SalaryRecord"]; prop = T["AdjustmentProposal"]; g = T["ComparableGroup"]
    q = lambda x: {k: round(float(v), 4) for k, v in x.describe(percentiles=[.05, .25, .5, .75, .95]).items()}
    lvl = T["Employee"].merge(sal.sort_values("effective_from").groupby("employee_id").tail(1)[["employee_id", "level_id"]], on="employee_id")
    return dict(
        employees=len(T["Employee"]), active=int((T["Employee"].status == "ACTIVE").sum()),
        salary_records=len(sal), salary_records_per_employee=round(len(sal) / len(T["Employee"]), 2),
        change_reason_counts=sal.change_reason.value_counts().to_dict(),
        currency_mix=sal.drop_duplicates("employee_id", keep="last").currency.value_counts().to_dict(),
        fte_mix=sal.fte.value_counts().sort_index().to_dict(),
        level_distribution=lvl.level_id.value_counts().reindex([f"L{i}" for i in range(1, 11)]).fillna(0).astype(int).to_dict(),
        compa_ratio_clean_rows=q(ok_s.compa_ratio), range_position_clean_rows=q(ok_s.range_position),
        pct_in_band_clean_rows=round(float((ok_s.range_position.between(0, 1)).mean()), 4),
        analysis_status=a.analysis_status.value_counts().to_dict(), exception_types=a.exception_type.value_counts().to_dict(),
        flagged=int(a.flag.sum()), flag_confidence=a.confidence.value_counts().to_dict(),
        comparable_groups=len(g), groups_meeting_min_size=int(g.min_size_met.sum()),
        groups_below_min_size=int((~g.min_size_met).sum()),
        proposals_by_status=prop.status.value_counts().to_dict(),
        model=analysis.attrs.get("model"),
    )
