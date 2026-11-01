import { useMemo, useState } from "react";
import { CircleCheck, CircleX, Flag, Layers, Users, WalletCards } from "lucide-react";
import { num } from "./data.js";
import { Card, DataTable, Hist, Kpi, Meter, Pill, fmt, humanize, pct } from "./ui.jsx";

const field = "h-9 rounded-lg border border-line bg-raised px-3 text-[13px] placeholder:text-muted pointer-coarse:h-11 pointer-coarse:text-base";
const grid4 = "grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4";

function Verdict({ v, m }) {
  const passed = v.status === "PASS";
  const totals = Object.values(m.detection).reduce((s, x) => ({ tp: s.tp + x.true_positive, fp: s.fp + x.false_positive, fn: s.fn + x.false_negative }), { tp: 0, fp: 0, fn: 0 });
  const stats = [
    { value: v.unexpected_errors.toLocaleString(), label: "Unexpected errors", sub: "must be 0" },
    { value: v.labelled_findings_observed.toLocaleString(), label: "Labelled findings caught", sub: `${v.missed_labelled} missed` },
    { value: pct(totals.tp / ((totals.tp + totals.fn) || 1)), label: "Detection recall", sub: `${totals.fn} false negatives` },
    { value: pct(totals.tp / ((totals.tp + totals.fp) || 1)), label: "Detection precision", sub: `${totals.fp} false positives` },
  ];
  return (
    <section className={`relative overflow-hidden rounded-2xl p-6 text-white shadow-lg sm:p-7 ${passed ? "bg-gradient-to-br from-[#0f2b5c] via-[#164488] to-[#1c5cab]" : "bg-gradient-to-br from-[#4c1414] via-[#7a1f1f] to-[#a12b2b]"}`}>
      <div className="pointer-events-none absolute -top-24 -right-16 size-72 rounded-full bg-white/[0.06]" aria-hidden="true" />
      <div className="relative grid items-center gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-1 text-xs font-semibold ring-1 ring-white/25">
            {passed ? <CircleCheck size={14} /> : <CircleX size={14} />}Validation {v.status}
          </span>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight sm:text-[28px]">{passed ? "The audit dataset passes validation" : "The audit dataset fails validation"}</h2>
          <p className="mt-2 max-w-xl text-[14px] text-blue-50/85">{v.checks_run.toLocaleString()} rule-based checks ran across {v.total_rows_checked.toLocaleString()} rows, with {v.unexpected_errors.toLocaleString()} unexpected errors and {v.missed_labelled.toLocaleString()} labelled findings missed.</p>
        </div>
        <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl bg-white/10 p-3.5 ring-1 ring-white/15">
              <dd className="text-2xl font-semibold tracking-tight">{s.value}</dd>
              <dt className="mt-1 text-xs font-medium text-white">{s.label}</dt>
              <p className="text-[11.5px] text-blue-50/75">{s.sub}</p>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

function ModelCard({ model }) {
  const rows = [["Performance rating", 0.05, model.rating_coef], ["Tenure (per year)", 0.012, model.tenure_coef], ["Documented premium", 1, model.premium_coef]];
  return (
    <Card title="Recovered pay model" sub="Fitted coefficients against the known true values" flush>
      <table className="w-full border-t border-line text-[12.5px]">
        <thead><tr className="text-xs text-ink-2">
          <th scope="col" className="px-5 py-2 text-left font-semibold">Coefficient</th>
          <th scope="col" className="px-2 py-2 text-right font-semibold">True</th>
          <th scope="col" className="px-2 py-2 text-right font-semibold">Recovered</th>
          <th scope="col" className="py-2 pr-5 pl-2 text-right font-semibold">Off by</th>
        </tr></thead>
        <tbody>{rows.map(([name, truth, got]) => (
          <tr key={name} className="border-t border-line/70">
            <td className="px-5 py-2.5 text-ink-2">{name}</td>
            <td className="px-2 py-2.5 text-right tabular-nums">{truth}</td>
            <td className="px-2 py-2.5 text-right font-semibold tabular-nums">{got.toFixed(4)}</td>
            <td className="py-2.5 pr-5 pl-2 text-right text-muted tabular-nums">{(Math.abs(got - truth) / truth * 100).toFixed(1)}%</td>
          </tr>
        ))}</tbody>
      </table>
      <dl className="grid grid-cols-3 gap-px border-t border-line bg-line">
        {[["Intercept", model.intercept.toFixed(4)], ["Robust sigma", fmt(model.robust_sigma)], ["Flag threshold", `|z| > ${model.z_threshold}`]].map(([k, val]) => (
          <div key={k} className="bg-surface px-3 py-3.5 text-center"><dd className="font-semibold tabular-nums">{val}</dd><dt className="mt-0.5 text-[11.5px] text-muted">{k}</dt></div>
        ))}
      </dl>
      <p className="rounded-b-2xl border-t border-line px-5 py-3.5 text-[12.5px] text-muted">True values are the coefficients the generator used. Recovering them from the data shows the model measures real pay drivers.</p>
    </Card>
  );
}

export function Overview({ data }) {
  const { metrics: m, validation: v, manifest } = data;
  const d = m.distributions, q = d.compa_ratio_clean_rows;
  const compa = useMemo(() => data.tables.PayGapAnalysis.filter((r) => r.analysis_status === "OK").map((r) => num(r.compa_ratio)), [data]);
  return (
    <>
      <Verdict v={v} m={m} />
      <div className={grid4}>
        <Kpi icon={Users} label="Employees" value={d.employees.toLocaleString()} sub={`${d.active.toLocaleString()} active`} />
        <Kpi icon={WalletCards} label="Salary records" value={d.salary_records.toLocaleString()} sub={`${d.salary_records_per_employee} per employee`} />
        <Kpi icon={Flag} label="Flagged (unexplained gap)" value={d.flagged.toLocaleString()} sub={`|z| > ${d.model.z_threshold}`} />
        <Kpi icon={Layers} label="Comparable groups" value={d.comparable_groups.toLocaleString()} sub={`${d.groups_below_min_size} below min size 5`} />
      </div>
      <Card title="Detection quality against ground truth" sub={`Ground truth is stored separately and never used as an input to the rules. Dataset seed ${manifest.seed}.`} flush>
        <div className="@container overflow-x-auto rounded-b-2xl border-t border-line">
          <table className="stack-table w-full text-[12.5px]">
            <thead><tr className="bg-raised text-xs text-ink-2">
              <th scope="col" className="px-5 py-2.5 text-left font-semibold">Issue type</th>
              {["Truth", "Detected", "TP", "FP", "FN"].map((h) => <th key={h} scope="col" className="px-3 py-2.5 text-right font-semibold">{h}</th>)}
              <th scope="col" className="px-3 py-2.5 text-right font-semibold">Precision</th>
              <th scope="col" className="px-5 py-2.5 text-right font-semibold">Recall</th>
            </tr></thead>
            <tbody>{Object.entries(m.detection).map(([k, x]) => (
              <tr key={k} className="border-t border-line/70 hover:bg-accent-soft/45">
                <td className="px-5 py-2.5 font-medium whitespace-nowrap" title={k}>{humanize(k)}</td>
                {[["Truth", x.ground_truth], ["Detected", x.detected], ["TP", x.true_positive]].map(([h, n]) => <td key={h} data-label={h} className="px-3 py-2.5 text-right tabular-nums">{n}</td>)}
                {[["FP", x.false_positive], ["FN", x.false_negative]].map(([h, n]) => <td key={h} data-label={h} className={`px-3 py-2.5 text-right tabular-nums ${n ? "font-semibold text-warn" : "text-muted"}`}>{n}</td>)}
                <td data-label="Precision" className="px-3 py-2.5"><Meter value={x.precision} /></td>
                <td data-label="Recall" className="px-5 py-2.5"><Meter value={x.recall} /></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </Card>
      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" title="Compa-ratio distribution (clean rows)" sub={`${pct(d.pct_in_band_clean_rows)} inside band. Percentiles: p5 ${fmt(q["5%"])}, p25 ${fmt(q["25%"])}, p75 ${fmt(q["75%"])}, p95 ${fmt(q["95%"])}`}>
          <Hist values={compa} lo={0.7} hi={1.5} step={0.02} median={q["50%"]} ticks={[0.7, 0.9, 1.1, 1.3, 1.5]} />
        </Card>
        <ModelCard model={d.model} />
      </div>
    </>
  );
}

export function Validation({ data }) {
  const v = data.validation, lab = v.labelled_findings_by_check;
  const rows = Object.entries(v.checks)
    .filter(([, c]) => c.violations)
    .map(([check, c]) => ({ check, rows_checked: c.rows_checked, violations: c.violations, verdict: lab[check] ? "expected (labelled anomaly)" : "UNEXPECTED" }))
    .sort((a, b) => b.violations - a.violations);
  return (
    <>
      <Card>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 pt-5 text-[13.5px] text-ink-2">
          <Pill value={v.status} />
          <span>{(v.checks_run - rows.length).toLocaleString()} of {v.checks_run.toLocaleString()} checks found nothing. PASS = 0 unexpected errors and every labelled anomaly caught by a rule-based check.</span>
        </div>
      </Card>
      <Card title="Checks with findings" sub="Violations on labelled anomalies are expected. The full list is in outputs/validation_summary.json." flush><DataTable rows={rows} /></Card>
      {v.unexpected_error_samples.length > 0 && <Card title="Unexpected error samples" sub="These rows fail validation" flush><DataTable rows={v.unexpected_error_samples} /></Card>}
    </>
  );
}

const Chip = ({ on, onClick, label, count }) => (
  <button aria-pressed={on} onClick={onClick}
    className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-[12.5px] font-medium transition-colors pointer-coarse:py-2.5 ${on ? "border-accent bg-accent-soft text-accent" : "border-line bg-surface text-ink-2 hover:bg-raised"}`}>
    {label}<span className="text-xs font-semibold tabular-nums opacity-80">{count}</span>
  </button>
);

export function Anomalies({ data, onOpen }) {
  const gt = data.tables.GroundTruth;
  const [f, setF] = useState("");
  const types = useMemo(() => {
    const c = new Map();
    for (const g of gt) c.set(g.issue_type, (c.get(g.issue_type) ?? 0) + 1);
    return [...c];
  }, [gt]);
  return (
    <>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by issue type">
        <Chip on={f === ""} onClick={() => setF("")} label="All" count={gt.length} />
        {types.map(([t, n]) => <Chip key={t} on={f === t} onClick={() => setF(t)} label={humanize(t)} count={n} />)}
      </div>
      <Card title="Planted anomalies (ground truth)" sub="Click an entity ID to see the real records behind the label and whether each rule passes or fails." flush>
        <DataTable key={f} rows={gt.filter((g) => !f || g.issue_type === f)} cols={["gt_id", "entity_type", "entity_id", "issue_type", "expected_decision", "context"]} onOpen={onOpen} />
      </Card>
    </>
  );
}

export function Gaps({ data, onOpen }) {
  const a = data.tables.PayGapAnalysis;
  const flagged = useMemo(() => a.filter((r) => r.flag === 1).sort((x, y) => Math.abs(num(y.residual_z)) - Math.abs(num(x.residual_z))), [a]);
  const exceptions = useMemo(() => a.filter((r) => r.exception_type), [a]);
  const props = data.tables.AdjustmentProposal;
  const [s, setS] = useState("");
  const statuses = [...new Set(props.map((p) => p.status))];
  return (
    <>
      <Card title={`Flagged: unexplained gap after documented factors (${flagged.length})`} sub="Sorted by largest absolute z-score" flush>
        <DataTable rows={flagged} onOpen={onOpen} cols={["employee_id", "group_id", "group_size", "rating", "tenure_years", "documented_premium_pct", "compa_ratio", "expected_compa", "residual_z", "flag_type", "confidence"]} />
      </Card>
      <Card title={`Exception queue (${exceptions.length})`} sub="Methodology defects, excluded from the model" flush>
        <DataTable rows={exceptions} onOpen={onOpen} cols={["snapshot_id", "employee_id", "exception_type", "compa_ratio", "band_position_status"]} />
      </Card>
      <Card title={`Adjustment proposals (${props.length})`} sub="Click an ID for the full audit trail" flush
        action={<label className="flex items-center gap-2 text-[12.5px] text-ink-2">Status
          <select className={field} value={s} onChange={(e) => setS(e.target.value)}><option value="">All</option>{statuses.map((x) => <option key={x} value={x}>{humanize(x)}</option>)}</select>
        </label>}>
        <DataTable key={s} rows={props.filter((p) => !s || p.status === s)} onOpen={onOpen} cols={["proposal_id", "employee_id", "trigger_type", "residual_z", "current_fte_salary", "proposed_fte_salary", "adjustment_pct", "status", "created_date", "evidence_summary"]} />
      </Card>
    </>
  );
}
