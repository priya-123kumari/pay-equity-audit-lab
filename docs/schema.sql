-- Auto-generated from generator/schema.py
PRAGMA foreign_keys = ON;

CREATE TABLE roles (
  role_id TEXT NOT NULL,
  role_name TEXT NOT NULL UNIQUE,
  role_family TEXT NOT NULL CHECK (role_family IN ('ENG', 'DATA', 'PRD', 'GTM', 'OPS', 'PPL')),
  l1_midpoint_usd REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'RETIRED')),
  PRIMARY KEY (role_id)
);

CREATE TABLE levels (
  level_id TEXT NOT NULL,
  level_number INTEGER NOT NULL UNIQUE,
  level_name TEXT NOT NULL,
  midpoint_multiplier REAL NOT NULL,
  range_spread_pct REAL NOT NULL,
  PRIMARY KEY (level_id)
);

CREATE TABLE locations (
  location_id TEXT NOT NULL,
  city TEXT NOT NULL,
  country TEXT NOT NULL,
  currency TEXT NOT NULL CHECK (currency IN ('USD', 'GBP', 'EUR', 'INR', 'SGD', 'CAD')),
  col_index REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'CLOSED')),
  PRIMARY KEY (location_id)
);

CREATE TABLE fx_rates (
  fx_id TEXT NOT NULL,
  currency TEXT NOT NULL CHECK (currency IN ('USD', 'GBP', 'EUR', 'INR', 'SGD', 'CAD')),
  rate_to_usd REAL NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE NOT NULL,
  PRIMARY KEY (fx_id)
);

CREATE TABLE compensation_bands (
  band_id TEXT NOT NULL,
  role_id TEXT NOT NULL,
  level_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  currency TEXT NOT NULL CHECK (currency IN ('USD', 'GBP', 'EUR', 'INR', 'SGD', 'CAD')),
  band_min REAL NOT NULL,
  band_mid REAL NOT NULL,
  band_max REAL NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE NOT NULL,
  version_year INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'EXPIRED')),
  supersedes_band_id TEXT,
  PRIMARY KEY (band_id),
  FOREIGN KEY (role_id) REFERENCES roles(role_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (level_id) REFERENCES levels(level_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (location_id) REFERENCES locations(location_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (supersedes_band_id) REFERENCES compensation_bands(band_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE employees (
  employee_id TEXT NOT NULL,
  hire_date DATE NOT NULL,
  termination_date DATE,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'TERMINATED')),
  manager_id TEXT,
  PRIMARY KEY (employee_id),
  FOREIGN KEY (manager_id) REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE tenures (
  tenure_id TEXT NOT NULL,
  employee_id TEXT NOT NULL UNIQUE,
  as_of_date DATE NOT NULL,
  tenure_months INTEGER NOT NULL,
  tenure_years REAL NOT NULL,
  tenure_band TEXT NOT NULL CHECK (tenure_band IN ('<1y', '1-3y', '3-5y', '5-10y', '10y+')),
  PRIMARY KEY (tenure_id),
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE salary_records (
  salary_id TEXT NOT NULL,
  employee_id TEXT NOT NULL,
  role_id TEXT NOT NULL,
  level_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  band_id TEXT NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE,
  currency TEXT NOT NULL CHECK (currency IN ('USD', 'GBP', 'EUR', 'INR', 'SGD', 'CAD')),
  fte REAL NOT NULL,
  base_salary REAL NOT NULL,
  change_reason TEXT NOT NULL CHECK (change_reason IN ('HIRE', 'ANNUAL_REVIEW', 'PROMOTION', 'FTE_CHANGE', 'RELOCATION_CURRENCY_CHANGE', 'OFF_CYCLE_ADJUSTMENT', 'PROPOSAL_ADJUSTMENT')),
  promotion_id TEXT,
  adjustment_id TEXT,
  PRIMARY KEY (salary_id),
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (role_id) REFERENCES roles(role_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (level_id) REFERENCES levels(level_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (location_id) REFERENCES locations(location_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (band_id) REFERENCES compensation_bands(band_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (promotion_id) REFERENCES promotions(promotion_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (adjustment_id) REFERENCES adjustment_proposals(proposal_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE performance_evidence (
  evidence_id TEXT NOT NULL,
  employee_id TEXT NOT NULL,
  evidence_type TEXT NOT NULL CHECK (evidence_type IN ('ANNUAL_REVIEW', 'CRITICAL_SKILL_PREMIUM', 'CERTIFICATION')),
  cycle_year INTEGER,
  rating INTEGER CHECK (rating IN (1, 2, 3, 4, 5)),
  pay_factor_pct REAL,
  effective_from DATE NOT NULL,
  recorded_date DATE NOT NULL,
  document_ref TEXT NOT NULL,
  PRIMARY KEY (evidence_id),
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE promotions (
  promotion_id TEXT NOT NULL,
  employee_id TEXT NOT NULL,
  role_id TEXT NOT NULL,
  from_level_id TEXT NOT NULL,
  to_level_id TEXT NOT NULL,
  effective_date DATE NOT NULL,
  pct_increase REAL NOT NULL,
  salary_id TEXT NOT NULL UNIQUE,
  PRIMARY KEY (promotion_id),
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (role_id) REFERENCES roles(role_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (from_level_id) REFERENCES levels(level_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (to_level_id) REFERENCES levels(level_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (salary_id) REFERENCES salary_records(salary_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE compa_ratio_snapshots (
  snapshot_id TEXT NOT NULL,
  snapshot_date DATE NOT NULL,
  employee_id TEXT NOT NULL,
  salary_id TEXT NOT NULL,
  band_id_used TEXT NOT NULL,
  salary_currency TEXT NOT NULL CHECK (salary_currency IN ('USD', 'GBP', 'EUR', 'INR', 'SGD', 'CAD')),
  band_currency TEXT NOT NULL CHECK (band_currency IN ('USD', 'GBP', 'EUR', 'INR', 'SGD', 'CAD')),
  fte REAL NOT NULL,
  fte_applied INTEGER NOT NULL CHECK (fte_applied IN (0,1)),
  fx_applied INTEGER NOT NULL CHECK (fx_applied IN (0,1)),
  fx_rate_used REAL,
  salary_used REAL NOT NULL,
  normalized_salary_usd REAL NOT NULL,
  band_min_usd REAL NOT NULL,
  band_mid_usd REAL NOT NULL,
  band_max_usd REAL NOT NULL,
  compa_ratio REAL NOT NULL,
  range_position REAL NOT NULL,
  PRIMARY KEY (snapshot_id),
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (salary_id) REFERENCES salary_records(salary_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (band_id_used) REFERENCES compensation_bands(band_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE comparable_groups (
  group_id TEXT NOT NULL,
  group_name TEXT NOT NULL,
  grouping_basis TEXT NOT NULL CHECK (grouping_basis IN ('RULE_BASED', 'MANUAL')),
  role_family TEXT CHECK (role_family IN ('ENG', 'DATA', 'PRD', 'GTM', 'OPS', 'PPL')),
  level_id TEXT,
  location_id TEXT,
  rationale TEXT,
  snapshot_date DATE NOT NULL,
  member_count INTEGER NOT NULL,
  min_size_met INTEGER NOT NULL CHECK (min_size_met IN (0,1)),
  status TEXT NOT NULL CHECK (status IN ('ACTIVE')),
  PRIMARY KEY (group_id),
  FOREIGN KEY (level_id) REFERENCES levels(level_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (location_id) REFERENCES locations(location_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE comparable_group_members (
  group_id TEXT NOT NULL,
  employee_id TEXT NOT NULL,
  role_id TEXT NOT NULL,
  level_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  joined_date DATE NOT NULL,
  PRIMARY KEY (group_id, employee_id),
  FOREIGN KEY (group_id) REFERENCES comparable_groups(group_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (role_id) REFERENCES roles(role_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (level_id) REFERENCES levels(level_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (location_id) REFERENCES locations(location_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE adjustment_proposals (
  proposal_id TEXT NOT NULL,
  employee_id TEXT NOT NULL,
  snapshot_id TEXT NOT NULL,
  salary_id TEXT NOT NULL,
  band_id TEXT NOT NULL,
  group_id TEXT NOT NULL,
  trigger_type TEXT NOT NULL CHECK (trigger_type IN ('BELOW_EXPECTED', 'ABOVE_EXPECTED')),
  residual_z REAL NOT NULL,
  currency TEXT NOT NULL CHECK (currency IN ('USD', 'GBP', 'EUR', 'INR', 'SGD', 'CAD')),
  current_fte_salary REAL NOT NULL,
  expected_fte_salary REAL NOT NULL,
  proposed_fte_salary REAL NOT NULL,
  fte REAL NOT NULL,
  proposed_base_salary REAL NOT NULL,
  adjustment_pct REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('DRAFT', 'SUBMITTED', 'MANAGER_APPROVED', 'HR_APPROVED', 'APPLIED', 'REJECTED')),
  created_date DATE NOT NULL,
  created_by TEXT NOT NULL,
  effective_date DATE,
  evidence_summary TEXT NOT NULL,
  PRIMARY KEY (proposal_id),
  FOREIGN KEY (employee_id) REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (snapshot_id) REFERENCES compa_ratio_snapshots(snapshot_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (salary_id) REFERENCES salary_records(salary_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (band_id) REFERENCES compensation_bands(band_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (group_id) REFERENCES comparable_groups(group_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (created_by) REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE approval_events (
  event_id TEXT NOT NULL,
  proposal_id TEXT NOT NULL,
  event_seq INTEGER NOT NULL,
  from_status TEXT CHECK (from_status IN ('DRAFT', 'SUBMITTED', 'MANAGER_APPROVED', 'HR_APPROVED', 'APPLIED', 'REJECTED')),
  to_status TEXT NOT NULL CHECK (to_status IN ('DRAFT', 'SUBMITTED', 'MANAGER_APPROVED', 'HR_APPROVED', 'APPLIED', 'REJECTED')),
  event_date DATE NOT NULL,
  actor_role TEXT NOT NULL CHECK (actor_role IN ('SYSTEM', 'HR_PARTNER', 'MANAGER', 'SYSTEM_ADMIN')),
  actor_id TEXT,
  comment TEXT,
  PRIMARY KEY (event_id),
  FOREIGN KEY (proposal_id) REFERENCES adjustment_proposals(proposal_id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (actor_id) REFERENCES employees(employee_id) DEFERRABLE INITIALLY DEFERRED
);
