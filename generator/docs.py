"""Generates docs/data_dictionary.md, docs/erd.md and docs/schema.sql from generator/schema.py."""
import os
from .schema import SCHEMA, TRANSITIONS, ISSUE_TYPES
from .export import ddl


def _fmt_allowed(a):
    if not a:
        return ""
    return ", ".join(str(x) for x in a) if len(a) <= 12 else f"{len(a)} values"


def data_dictionary():
    L = ["# Data Dictionary", "",
         "Generated from `generator/schema.py` (single source of truth). BOOLEAN columns are exported as `0/1`; dates are ISO-8601 (`YYYY-MM-DD`).",
         "Money is stored in **local currency, annual**. `base_salary` is the amount actually paid (pro-rated by FTE); "
         "FTE-equivalent salary = `base_salary / fte`. Normalisation to USD uses `FXRate`.", ""]
    L += ["## Entities and cardinality", "", "| Entity | Primary key | Description | Cardinality / relationships |", "|---|---|---|---|"]
    for n, s in SCHEMA.items():
        L.append(f"| {n} | `{', '.join(s['pk'])}` | {s['desc']} | {s['cardinality']} |")
    for n, s in SCHEMA.items():
        L += ["", f"## {n}  (`{s['file']}.csv`)", "", s["desc"], "", f"*Primary key:* `{', '.join(s['pk'])}`  ", f"*Cardinality:* {s['cardinality']}", "",
              "| Field | Type | Required | Allowed values | Unit | Unique | Validation rule | Foreign key |", "|---|---|---|---|---|---|---|---|"]
        for nm, typ, req, allowed, unit, uniq, rule, fk in s["cols"]:
            u = "yes" if uniq or (nm in s["pk"] and len(s["pk"]) == 1) else ""
            L.append(f"| `{nm}` | {typ} | {'yes' if req else 'optional'} | {_fmt_allowed(allowed)} | {unit or ''} | {u} | {rule.replace('|', '/')} | {('`' + fk + '`') if fk else ''} |")
    L += ["", "## Lifecycle: AdjustmentProposal", "", "Legal transitions (enforced by `validate.py`, recorded one row per change in `ApprovalEvent`):", ""]
    for a, b in TRANSITIONS.items():
        L.append(f"- `{a or '(create)'}` → {', '.join('`' + x + '`' for x in b) if b else '*(terminal)*'}")
    L += ["", "## Lifecycle: CompensationBand", "", "`ACTIVE` while the effective period covers the AS_OF date, otherwise `EXPIRED`. A new version is added each year; old rows are never edited.",
          "", "## Ground-truth issue types (kept in `ground_truth/`, never in input tables)", ""]
    L += [f"- `{t}`" for t in ISSUE_TYPES]
    return "\n".join(L) + "\n"


def erd():
    L = ["# Entity-Relationship Diagram", "", "```mermaid", "erDiagram"]
    for n, s in SCHEMA.items():
        for c in s["cols"]:
            if c[7]:
                pt = c[7].split(".")[0]
                card = "|o--o{" if not c[2] else "||--o{"
                if n == "Tenure" and c[0] == "employee_id":
                    card = "||--||"
                L.append(f"    {pt} {card} {n} : \"{c[0]}\"")
    L.append("    Employee ||--o{ ComparableGroupMember : \"member of (N:M via bridge)\"")
    L += ["```", "", "Cardinality summary: see the table in `data_dictionary.md`. The only N:M relationship is "
          "**Employee ↔ ComparableGroup**, resolved by the bridge table `ComparableGroupMember`."]
    return "\n".join(L) + "\n"


def write_docs(d):
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "data_dictionary.md"), "w", encoding="utf-8", newline="\n").write(data_dictionary())
    open(os.path.join(d, "erd.md"), "w", encoding="utf-8", newline="\n").write(erd())
    open(os.path.join(d, "schema.sql"), "w", encoding="utf-8", newline="\n").write(ddl())
