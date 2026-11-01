import { useEffect, useState } from "react";

/** [table name used in the UI, exported json file name] */
export const TABLES = [
  ["Role", "roles"], ["Level", "levels"], ["Location", "locations"], ["FXRate", "fx_rates"],
  ["CompensationBand", "compensation_bands"], ["Employee", "employees"], ["Tenure", "tenures"],
  ["SalaryRecord", "salary_records"], ["PerformanceEvidence", "performance_evidence"], ["Promotion", "promotions"],
  ["CompaRatioSnapshot", "compa_ratio_snapshots"], ["ComparableGroup", "comparable_groups"],
  ["ComparableGroupMember", "comparable_group_members"], ["AdjustmentProposal", "adjustment_proposals"],
  ["ApprovalEvent", "approval_events"],
];

export const num = (v) => (typeof v === "number" ? v : Number(v ?? 0));
export const str = (v) => (v === null || v === undefined ? "" : String(v));
const url = (p) => `${import.meta.env.BASE_URL}data/${p}`;

async function getJson(p) {
  const r = await fetch(url(p));
  if (!r.ok) throw new Error(`${p}: HTTP ${r.status}`);
  return r.json();
}

const conv = (s) => (s === "" ? null : /^-?\d+(\.\d+)?$/.test(s) ? Number(s) : s);

/** Minimal CSV parser (handles quoted commas, quotes and newlines). */
export function parseCsv(text) {
  const rows = [];
  let row = [], cur = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else quoted = false; }
      else cur += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(cur); cur = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cur); cur = ""; rows.push(row); row = [];
    } else cur += c;
  }
  if (cur !== "" || row.length) { row.push(cur); rows.push(row); }
  const [head, ...body] = rows;
  return body.filter((r) => r.length === head.length).map((r) => Object.fromEntries(head.map((h, i) => [h, conv(r[i])])));
}

/** get(table, column, value) -> rows; builds each index lazily once. */
export function makeLookup(tables) {
  const cache = new Map();
  return (table, col, val) => {
    const k = `${table}.${col}`;
    let m = cache.get(k);
    if (!m) {
      m = new Map();
      for (const r of tables[table] ?? []) {
        const key = str(r[col]);
        if (m.has(key)) m.get(key).push(r); else m.set(key, [r]);
      }
      cache.set(k, m);
    }
    return m.get(str(val)) ?? [];
  };
}

export function useData() {
  const [state, setState] = useState({});
  useEffect(() => {
    (async () => {
      try {
        const rows = await Promise.all(TABLES.map(([, f]) => getJson(`json/${f}.json`)));
        const [groundTruth, validation, metrics, manifest, csv] = await Promise.all([
          getJson("ground_truth/ground_truth.json"), getJson("outputs/validation_summary.json"),
          getJson("outputs/evaluation_metrics.json"), getJson("manifest/source_manifest.json"),
          fetch(url("outputs/pay_gap_analysis.csv")).then((r) => r.text()),
        ]);
        const tables = Object.fromEntries(TABLES.map(([n], i) => [n, rows[i]]));
        tables.PayGapAnalysis = parseCsv(csv);
        tables.GroundTruth = groundTruth;
        setState({ data: { tables, validation, metrics, manifest } });
      } catch (e) {
        setState({ error: String(e) });
      }
    })();
  }, []);
  return state;
}
