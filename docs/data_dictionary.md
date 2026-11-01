# Data Dictionary

Generated from `generator/schema.py` (single source of truth). BOOLEAN columns are exported as `0/1`; dates are ISO-8601 (`YYYY-MM-DD`).
Money is stored in **local currency, annual**. `base_salary` is the amount actually paid (pro-rated by FTE); FTE-equivalent salary = `base_salary / fte`. Normalisation to USD uses `FXRate`.

## Entities and cardinality

| Entity | Primary key | Description | Cardinality / relationships |
|---|---|---|---|
| Role | `role_id` | Job role (master data). 20 roles in 6 families. | Role 1:N CompensationBand; Role 1:N SalaryRecord |
| Level | `level_id` | Job level L1..L10 (master data). Midpoint multiplier compounds 13% per level. | Level 1:N CompensationBand; Level 1:N SalaryRecord |
| Location | `location_id` | Pay location with local currency and cost-of-living index. | Location 1:N CompensationBand; Location 1:N SalaryRecord |
| FXRate | `fx_id` | Effective-dated currency conversion (synthetic) to USD. | Currency 1:N FXRate (one row per currency per year) |
| CompensationBand | `band_id` | Effective-dated pay band per role/level/location. One version per year; older versions are EXPIRED. | Role/Level/Location 1:N Band; Band supersedes Band (optional self-reference); Band 1:N SalaryRecord |
| Employee | `employee_id` | Employee master record. Pay/position history lives in SalaryRecord (never overwritten). | Employee 1:N SalaryRecord; Employee 1:1 Tenure; Employee 1:N PerformanceEvidence; Employee 1:N Promotion; Employee N:1 Employee (manager, optional) |
| Tenure | `tenure_id` | Tenure derived from hire/termination date as of the snapshot (derived, 1:1 with Employee). | Employee 1:1 Tenure |
| SalaryRecord | `salary_id` | Effective-dated salary/position event. Every change adds a row; history is never overwritten. | Employee 1:N SalaryRecord; SalaryRecord N:1 Role/Level/Location/Band; SalaryRecord 0..1:1 Promotion; SalaryRecord 0..1:1 AdjustmentProposal |
| PerformanceEvidence | `evidence_id` | Documented pay factors: annual review ratings and approved premiums (critical skill, certification). | Employee 1:N PerformanceEvidence |
| Promotion | `promotion_id` | Level promotion event with the resulting salary record. | Employee 1:N Promotion; Promotion 1:1 SalaryRecord |
| CompaRatioSnapshot | `snapshot_id` | Derived compa-ratio and range position per active employee on the snapshot date. Records the METHOD used (band, FTE, FX). | Employee 1:1 snapshot (per date); SalaryRecord 1:N snapshot; Band 1:N snapshot |
| ComparableGroup | `group_id` | Peer group used for pay comparison. RULE_BASED = same role family + level + location. MANUAL groups need a rationale. | ComparableGroup N:M Employee via ComparableGroupMember |
| ComparableGroupMember | `group_id, employee_id` | Bridge table for the N:M relationship Employee <-> ComparableGroup. | Employee N:M ComparableGroup |
| AdjustmentProposal | `proposal_id` | Pay-adjustment proposal raised for an unexplained gap, with evidence and lifecycle state. | Employee 1:N Proposal; Proposal 1:N ApprovalEvent; Proposal 0..1:1 SalaryRecord (when APPLIED) |
| ApprovalEvent | `event_id` | Append-only audit trail: one row per proposal state change. | AdjustmentProposal 1:N ApprovalEvent |

## Role  (`roles.csv`)

Job role (master data). 20 roles in 6 families.

*Primary key:* `role_id`  
*Cardinality:* Role 1:N CompensationBand; Role 1:N SalaryRecord

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `role_id` | TEXT | yes |  |  | yes | ^[A-Z]{2,6}$ |  |
| `role_name` | TEXT | yes |  |  | yes |  |  |
| `role_family` | TEXT | yes | ENG, DATA, PRD, GTM, OPS, PPL |  |  | comparability family |  |
| `l1_midpoint_usd` | REAL | yes |  | USD/yr |  | > 0; band midpoint at Level 1, US cost of living |  |
| `status` | TEXT | yes | ACTIVE, RETIRED |  |  |  |  |

## Level  (`levels.csv`)

Job level L1..L10 (master data). Midpoint multiplier compounds 13% per level.

*Primary key:* `level_id`  
*Cardinality:* Level 1:N CompensationBand; Level 1:N SalaryRecord

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `level_id` | TEXT | yes |  |  | yes | ^L([1-9]/10)$ |  |
| `level_number` | INTEGER | yes |  |  | yes | 1..10 |  |
| `level_name` | TEXT | yes |  |  |  |  |  |
| `midpoint_multiplier` | REAL | yes |  |  |  | 1.13^(level_number-1) |  |
| `range_spread_pct` | REAL | yes |  | fraction |  | (max-min)/mid; 0.30 at L1 rising to 0.39 at L10 |  |

## Location  (`locations.csv`)

Pay location with local currency and cost-of-living index.

*Primary key:* `location_id`  
*Cardinality:* Location 1:N CompensationBand; Location 1:N SalaryRecord

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `location_id` | TEXT | yes |  |  | yes | ^[A-Z]{3}$ |  |
| `city` | TEXT | yes |  |  |  |  |  |
| `country` | TEXT | yes |  |  |  |  |  |
| `currency` | TEXT | yes | USD, GBP, EUR, INR, SGD, CAD |  |  |  |  |
| `col_index` | REAL | yes |  |  |  | > 0; US=1.0 |  |
| `status` | TEXT | yes | ACTIVE, CLOSED |  |  |  |  |

## FXRate  (`fx_rates.csv`)

Effective-dated currency conversion (synthetic) to USD.

*Primary key:* `fx_id`  
*Cardinality:* Currency 1:N FXRate (one row per currency per year)

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `fx_id` | TEXT | yes |  |  | yes | ^FX-[A-Z]{3}-\d{4}$ |  |
| `currency` | TEXT | yes | USD, GBP, EUR, INR, SGD, CAD |  |  |  |  |
| `rate_to_usd` | REAL | yes |  | USD per 1 unit |  | > 0 |  |
| `effective_from` | DATE | yes |  |  |  |  |  |
| `effective_to` | DATE | yes |  |  |  | >= effective_from |  |

## CompensationBand  (`compensation_bands.csv`)

Effective-dated pay band per role/level/location. One version per year; older versions are EXPIRED.

*Primary key:* `band_id`  
*Cardinality:* Role/Level/Location 1:N Band; Band supersedes Band (optional self-reference); Band 1:N SalaryRecord

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `band_id` | TEXT | yes |  |  | yes | ^BAND-[A-Z]+-L\d{1,2}-[A-Z]{3}-\d{4}$ i.e. BAND-<role>-<level>-<location>-<year> |  |
| `role_id` | TEXT | yes |  |  |  |  | `Role.role_id` |
| `level_id` | TEXT | yes |  |  |  |  | `Level.level_id` |
| `location_id` | TEXT | yes |  |  |  |  | `Location.location_id` |
| `currency` | TEXT | yes | USD, GBP, EUR, INR, SGD, CAD |  |  | = Location.currency |  |
| `band_min` | REAL | yes |  | local currency/yr, FTE=1.0 |  | 0 < min < mid |  |
| `band_mid` | REAL | yes |  | local currency/yr, FTE=1.0 |  | min < mid < max |  |
| `band_max` | REAL | yes |  | local currency/yr, FTE=1.0 |  | > mid |  |
| `effective_from` | DATE | yes |  |  |  |  |  |
| `effective_to` | DATE | yes |  |  |  | >= effective_from |  |
| `version_year` | INTEGER | yes |  |  |  | = year(effective_from) |  |
| `status` | TEXT | yes | ACTIVE, EXPIRED |  |  | ACTIVE iff effective period covers AS_OF date |  |
| `supersedes_band_id` | TEXT | optional |  |  |  |  | `CompensationBand.band_id` |

## Employee  (`employees.csv`)

Employee master record. Pay/position history lives in SalaryRecord (never overwritten).

*Primary key:* `employee_id`  
*Cardinality:* Employee 1:N SalaryRecord; Employee 1:1 Tenure; Employee 1:N PerformanceEvidence; Employee 1:N Promotion; Employee N:1 Employee (manager, optional)

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `employee_id` | TEXT | yes |  |  | yes | ^EMP-\d{6}$ |  |
| `hire_date` | DATE | yes |  |  |  | <= first SalaryRecord.effective_from |  |
| `termination_date` | DATE | optional |  |  |  | > hire_date; null iff ACTIVE |  |
| `status` | TEXT | yes | ACTIVE, TERMINATED |  |  |  |  |
| `manager_id` | TEXT | optional |  |  |  |  | `Employee.employee_id` |

## Tenure  (`tenures.csv`)

Tenure derived from hire/termination date as of the snapshot (derived, 1:1 with Employee).

*Primary key:* `tenure_id`  
*Cardinality:* Employee 1:1 Tenure

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `tenure_id` | TEXT | yes |  |  | yes | ^TEN-\d{6}$ |  |
| `employee_id` | TEXT | yes |  |  | yes |  | `Employee.employee_id` |
| `as_of_date` | DATE | yes |  |  |  | min(snapshot date, termination_date) |  |
| `tenure_months` | INTEGER | yes |  | months |  | whole months hire_date -> as_of_date |  |
| `tenure_years` | REAL | yes |  | years |  | (as_of_date-hire_date)/365.25, 2dp |  |
| `tenure_band` | TEXT | yes | <1y, 1-3y, 3-5y, 5-10y, 10y+ |  |  |  |  |

## SalaryRecord  (`salary_records.csv`)

Effective-dated salary/position event. Every change adds a row; history is never overwritten.

*Primary key:* `salary_id`  
*Cardinality:* Employee 1:N SalaryRecord; SalaryRecord N:1 Role/Level/Location/Band; SalaryRecord 0..1:1 Promotion; SalaryRecord 0..1:1 AdjustmentProposal

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `salary_id` | TEXT | yes |  |  | yes | ^SAL-EMP-\d{6}-\d{4}-\d{2}$ i.e. SAL-<employee-id>-<year>-<seq> |  |
| `employee_id` | TEXT | yes |  |  |  |  | `Employee.employee_id` |
| `role_id` | TEXT | yes |  |  |  |  | `Role.role_id` |
| `level_id` | TEXT | yes |  |  |  |  | `Level.level_id` |
| `location_id` | TEXT | yes |  |  |  |  | `Location.location_id` |
| `band_id` | TEXT | yes |  |  |  | band for role/level/location effective on effective_from | `CompensationBand.band_id` |
| `effective_from` | DATE | yes |  |  |  |  |  |
| `effective_to` | DATE | optional |  |  |  | next record's effective_from - 1 day; null = current |  |
| `currency` | TEXT | yes | USD, GBP, EUR, INR, SGD, CAD |  |  | = Location.currency |  |
| `fte` | REAL | yes |  | fraction |  | 0.5 <= fte <= 1.0 |  |
| `base_salary` | REAL | yes |  | local currency/yr, actually paid (pro-rated by FTE) |  | > 0; FTE-equivalent salary = base_salary / fte |  |
| `change_reason` | TEXT | yes | HIRE, ANNUAL_REVIEW, PROMOTION, FTE_CHANGE, RELOCATION_CURRENCY_CHANGE, OFF_CYCLE_ADJUSTMENT, PROPOSAL_ADJUSTMENT |  |  |  |  |
| `promotion_id` | TEXT | optional |  |  |  | required iff PROMOTION | `Promotion.promotion_id` |
| `adjustment_id` | TEXT | optional |  |  |  | required iff PROPOSAL_ADJUSTMENT | `AdjustmentProposal.proposal_id` |

## PerformanceEvidence  (`performance_evidence.csv`)

Documented pay factors: annual review ratings and approved premiums (critical skill, certification).

*Primary key:* `evidence_id`  
*Cardinality:* Employee 1:N PerformanceEvidence

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `evidence_id` | TEXT | yes |  |  | yes | ^PEV-\d{6}$ |  |
| `employee_id` | TEXT | yes |  |  |  |  | `Employee.employee_id` |
| `evidence_type` | TEXT | yes | ANNUAL_REVIEW, CRITICAL_SKILL_PREMIUM, CERTIFICATION |  |  |  |  |
| `cycle_year` | INTEGER | optional |  |  |  | required iff ANNUAL_REVIEW |  |
| `rating` | INTEGER | optional | 1, 2, 3, 4, 5 |  |  | required iff ANNUAL_REVIEW |  |
| `pay_factor_pct` | REAL | optional |  | fraction |  | required iff premium types; 0 < x <= 0.20 |  |
| `effective_from` | DATE | yes |  |  |  |  |  |
| `recorded_date` | DATE | yes |  |  |  | >= hire_date |  |
| `document_ref` | TEXT | yes |  |  |  |  |  |

## Promotion  (`promotions.csv`)

Level promotion event with the resulting salary record.

*Primary key:* `promotion_id`  
*Cardinality:* Employee 1:N Promotion; Promotion 1:1 SalaryRecord

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `promotion_id` | TEXT | yes |  |  | yes | ^PRM-\d{6}$ |  |
| `employee_id` | TEXT | yes |  |  |  |  | `Employee.employee_id` |
| `role_id` | TEXT | yes |  |  |  |  | `Role.role_id` |
| `from_level_id` | TEXT | yes |  |  |  |  | `Level.level_id` |
| `to_level_id` | TEXT | yes |  |  |  | level_number = from + 1 | `Level.level_id` |
| `effective_date` | DATE | yes |  |  |  |  |  |
| `pct_increase` | REAL | yes |  | fraction |  | 0.08..0.15; = new/old FTE-equivalent salary - 1 |  |
| `salary_id` | TEXT | yes |  |  | yes |  | `SalaryRecord.salary_id` |

## CompaRatioSnapshot  (`compa_ratio_snapshots.csv`)

Derived compa-ratio and range position per active employee on the snapshot date. Records the METHOD used (band, FTE, FX).

*Primary key:* `snapshot_id`  
*Cardinality:* Employee 1:1 snapshot (per date); SalaryRecord 1:N snapshot; Band 1:N snapshot

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `snapshot_id` | TEXT | yes |  |  | yes | ^CRS-EMP-\d{6}-\d{4}-\d{2}$ |  |
| `snapshot_date` | DATE | yes |  |  |  |  |  |
| `employee_id` | TEXT | yes |  |  |  |  | `Employee.employee_id` |
| `salary_id` | TEXT | yes |  |  |  | record effective on snapshot_date | `SalaryRecord.salary_id` |
| `band_id_used` | TEXT | yes |  |  |  | should be effective on snapshot_date | `CompensationBand.band_id` |
| `salary_currency` | TEXT | yes | USD, GBP, EUR, INR, SGD, CAD |  |  |  |  |
| `band_currency` | TEXT | yes | USD, GBP, EUR, INR, SGD, CAD |  |  |  |  |
| `fte` | REAL | yes |  | fraction |  |  |  |
| `fte_applied` | BOOLEAN | yes |  |  |  | salary_used = base/fte if 1 else base |  |
| `fx_applied` | BOOLEAN | yes |  |  |  | if 1, normalized = salary_used * fx_rate_used |  |
| `fx_rate_used` | REAL | optional |  | USD per 1 unit |  | null iff fx_applied = 0 |  |
| `salary_used` | REAL | yes |  | local currency/yr |  |  |  |
| `normalized_salary_usd` | REAL | yes |  | USD/yr |  |  |  |
| `band_min_usd` | REAL | yes |  | USD/yr |  |  |  |
| `band_mid_usd` | REAL | yes |  | USD/yr |  |  |  |
| `band_max_usd` | REAL | yes |  | USD/yr |  |  |  |
| `compa_ratio` | REAL | yes |  |  |  | normalized_salary_usd / band_mid_usd |  |
| `range_position` | REAL | yes |  |  |  | (normalized - band_min) / (band_max - band_min); <0 below band, >1 above |  |

## ComparableGroup  (`comparable_groups.csv`)

Peer group used for pay comparison. RULE_BASED = same role family + level + location. MANUAL groups need a rationale.

*Primary key:* `group_id`  
*Cardinality:* ComparableGroup N:M Employee via ComparableGroupMember

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `group_id` | TEXT | yes |  |  | yes | CG-<family>-<level>-<location> or CG-MANUAL-nnnn |  |
| `group_name` | TEXT | yes |  |  |  |  |  |
| `grouping_basis` | TEXT | yes | RULE_BASED, MANUAL |  |  |  |  |
| `role_family` | TEXT | optional | ENG, DATA, PRD, GTM, OPS, PPL |  |  |  |  |
| `level_id` | TEXT | optional |  |  |  |  | `Level.level_id` |
| `location_id` | TEXT | optional |  |  |  |  | `Location.location_id` |
| `rationale` | TEXT | optional |  |  |  | mandatory when members span >1 role family |  |
| `snapshot_date` | DATE | yes |  |  |  |  |  |
| `member_count` | INTEGER | yes |  |  |  | = count of bridge rows |  |
| `min_size_met` | BOOLEAN | yes |  |  |  | member_count >= 5 |  |
| `status` | TEXT | yes | ACTIVE |  |  |  |  |

## ComparableGroupMember  (`comparable_group_members.csv`)

Bridge table for the N:M relationship Employee <-> ComparableGroup.

*Primary key:* `group_id, employee_id`  
*Cardinality:* Employee N:M ComparableGroup

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `group_id` | TEXT | yes |  |  |  |  | `ComparableGroup.group_id` |
| `employee_id` | TEXT | yes |  |  |  |  | `Employee.employee_id` |
| `role_id` | TEXT | yes |  |  |  |  | `Role.role_id` |
| `level_id` | TEXT | yes |  |  |  |  | `Level.level_id` |
| `location_id` | TEXT | yes |  |  |  |  | `Location.location_id` |
| `joined_date` | DATE | yes |  |  |  |  |  |

## AdjustmentProposal  (`adjustment_proposals.csv`)

Pay-adjustment proposal raised for an unexplained gap, with evidence and lifecycle state.

*Primary key:* `proposal_id`  
*Cardinality:* Employee 1:N Proposal; Proposal 1:N ApprovalEvent; Proposal 0..1:1 SalaryRecord (when APPLIED)

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `proposal_id` | TEXT | yes |  |  | yes | ^ADJ-2026-\d{6}$ |  |
| `employee_id` | TEXT | yes |  |  |  |  | `Employee.employee_id` |
| `snapshot_id` | TEXT | yes |  |  |  |  | `CompaRatioSnapshot.snapshot_id` |
| `salary_id` | TEXT | yes |  |  |  |  | `SalaryRecord.salary_id` |
| `band_id` | TEXT | yes |  |  |  |  | `CompensationBand.band_id` |
| `group_id` | TEXT | yes |  |  |  |  | `ComparableGroup.group_id` |
| `trigger_type` | TEXT | yes | BELOW_EXPECTED, ABOVE_EXPECTED |  |  |  |  |
| `residual_z` | REAL | yes |  |  |  | robust z of unexplained gap |  |
| `currency` | TEXT | yes | USD, GBP, EUR, INR, SGD, CAD |  |  |  |  |
| `current_fte_salary` | REAL | yes |  | local/yr |  | base_salary / fte |  |
| `expected_fte_salary` | REAL | yes |  | local/yr |  |  |  |
| `proposed_fte_salary` | REAL | yes |  | local/yr |  |  |  |
| `fte` | REAL | yes |  |  |  |  |  |
| `proposed_base_salary` | REAL | yes |  | local/yr |  | round(proposed_fte_salary * fte) |  |
| `adjustment_pct` | REAL | yes |  | fraction |  | proposed_fte/current_fte - 1 |  |
| `status` | TEXT | yes | DRAFT, SUBMITTED, MANAGER_APPROVED, HR_APPROVED, APPLIED, REJECTED |  |  | = to_status of last ApprovalEvent |  |
| `created_date` | DATE | yes |  |  |  |  |  |
| `created_by` | TEXT | yes |  |  |  | HR partner | `Employee.employee_id` |
| `effective_date` | DATE | optional |  |  |  | set iff APPLIED |  |
| `evidence_summary` | TEXT | yes |  |  |  |  |  |

## ApprovalEvent  (`approval_events.csv`)

Append-only audit trail: one row per proposal state change.

*Primary key:* `event_id`  
*Cardinality:* AdjustmentProposal 1:N ApprovalEvent

| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |
|---|---|---|---|---|---|---|---|
| `event_id` | TEXT | yes |  |  | yes | ^AEV-\d{6}$ |  |
| `proposal_id` | TEXT | yes |  |  |  |  | `AdjustmentProposal.proposal_id` |
| `event_seq` | INTEGER | yes |  |  |  | 1..n contiguous per proposal |  |
| `from_status` | TEXT | optional | DRAFT, SUBMITTED, MANAGER_APPROVED, HR_APPROVED, APPLIED, REJECTED |  |  | null only for creation |  |
| `to_status` | TEXT | yes | DRAFT, SUBMITTED, MANAGER_APPROVED, HR_APPROVED, APPLIED, REJECTED |  |  | must be a legal transition |  |
| `event_date` | DATE | yes |  |  |  | non-decreasing per proposal |  |
| `actor_role` | TEXT | yes | SYSTEM, HR_PARTNER, MANAGER, SYSTEM_ADMIN |  |  |  |  |
| `actor_id` | TEXT | optional |  |  |  | null for SYSTEM / SYSTEM_ADMIN | `Employee.employee_id` |
| `comment` | TEXT | optional |  |  |  |  |  |

## Lifecycle: AdjustmentProposal

Legal transitions (enforced by `validate.py`, recorded one row per change in `ApprovalEvent`):

- `(create)` → `DRAFT`
- `DRAFT` → `SUBMITTED`
- `SUBMITTED` → `MANAGER_APPROVED`, `REJECTED`
- `MANAGER_APPROVED` → `HR_APPROVED`, `REJECTED`
- `HR_APPROVED` → `APPLIED`, `REJECTED`
- `APPLIED` → *(terminal)*
- `REJECTED` → *(terminal)*

## Lifecycle: CompensationBand

`ACTIVE` while the effective period covers the AS_OF date, otherwise `EXPIRED`. A new version is added each year; old rows are never edited.

## Ground-truth issue types (kept in `ground_truth/`, never in input tables)

- `UNEXPLAINED_OUTLIER`
- `EXPIRED_BAND_COMPARISON`
- `FTE_IGNORED`
- `CURRENCY_CONVERSION_MISSING`
- `ADJUSTMENT_WITHOUT_APPROVAL`
- `INCOMPARABLE_GROUP_NO_RATIONALE`
