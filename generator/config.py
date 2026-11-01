"""Run configuration. Every knob lives here so starter and full datasets share one generator."""
from dataclasses import dataclass
from datetime import date
import math

SEED = 20261022
HISTORY_START = date(2024, 1, 1)      # 3 years of salary history: 2024, 2025, 2026
SNAPSHOT_DATE = date(2026, 10, 1)     # date on which compa-ratios are measured
AS_OF_DATE = date(2026, 10, 22)       # "today" for the dataset; no datetime.now() anywhere
HIRE_REF_DATE = date(2026, 6, 30)     # latest possible hire date
REPORTING_CURRENCY = "USD"
MIN_GROUP_SIZE = 5                    # comparable group must have >= 5 members
Z_THRESHOLD = 3.5                     # robust z-score for "unexplained gap"


@dataclass
class Config:
    seed: int = SEED
    employees: int = 5000
    pay_noise_sd: float = 0.035          # idiosyncratic (normal) pay noise
    outlier_rate: float = 0.015          # deliberate unexplained outliers
    expired_band_rate: float = 0.008
    fte_ignored_rate: float = 0.008
    currency_missing_rate: float = 0.006
    unapproved_share: float = 0.08       # share of proposals flipped to "applied without approval"
    incomparable_group_rate: float = 0.0016
    min_count: int = 2                   # floor so tiny starter datasets still show every edge case

    def count(self, rate: float, floor: int | None = None) -> int:
        return max(self.min_count if floor is None else floor, math.ceil(rate * self.employees))
