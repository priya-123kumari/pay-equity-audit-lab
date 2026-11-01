import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDown, ArrowUp, ChevronsUpDown, CircleAlert, CircleCheck, CircleDot, CircleX, X } from "lucide-react";

export const ENTITY = /^(EMP-\d{6}|CRS-EMP-\d{6}-\d{4}-\d{2}|ADJ-\d{4}-\d{6}|CG-[A-Z0-9-]+)$/;
export const fmt = (v) => (v === null || v === undefined ? "-" : typeof v === "number" ? (Number.isInteger(v) ? String(v) : String(+v.toFixed(4))) : v);
export const pct = (v) => (v === null || v === undefined ? "n/a" : `${(v * 100).toFixed(1)}%`);
export const humanize = (s) => {
  const t = String(s).replace(/_/g, " ").toLowerCase().replace(/\b(fte|fx|hr)\b/g, (a) => a.toUpperCase());
  return t.charAt(0).toUpperCase() + t.slice(1);
};

const TONES = {
  good: { box: "bg-good-soft text-good", icon: CircleCheck },
  warn: { box: "bg-warn-soft text-warn", icon: CircleAlert },
  bad: { box: "bg-bad-soft text-bad", icon: CircleX },
  info: { box: "bg-accent-soft text-accent", icon: CircleDot },
  neutral: { box: "bg-raised text-ink-2 ring-1 ring-inset ring-line", icon: CircleDot },
};
const STATUS_TONE = {
  PASS: "good", pass: "good", OK: "good", APPLIED: "good",
  HR_APPROVED: "info", MANAGER_APPROVED: "info",
  "expected (labelled anomaly)": "warn",
  FAIL: "bad", UNEXPECTED: "bad", REJECTED: "bad", EXCEPTION: "bad",
};
const STATUS_COLUMNS = new Set(["status", "verdict", "analysis_status", "confidence"]);

export function Pill({ value }) {
  const t = TONES[STATUS_TONE[value] ?? "neutral"];
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11.5px] font-semibold whitespace-nowrap ${t.box}`}><t.icon size={12} aria-hidden="true" />{value}</span>;
}

export const Card = ({ title, sub, action, flush, className = "", children }) => (
  <section className={`min-w-0 rounded-2xl border border-line bg-surface shadow-sm shadow-slate-900/[0.03] ${className}`}>
    {(title || action) && (
      <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 px-5 pt-4 pb-3">
        <div className="min-w-0"><h2 className="text-[14.5px] font-semibold tracking-tight">{title}</h2>{sub && <p className="mt-0.5 text-[12.5px] text-muted">{sub}</p>}</div>
        {action}
      </header>
    )}
    <div className={flush ? "" : "px-5 pb-5"}>{children}</div>
  </section>
);

export const Kpi = ({ icon: Icon, label, value, sub, tone }) => (
  <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm shadow-slate-900/[0.03]">
    <div className="flex items-center justify-between gap-2">
      <span className="text-[12.5px] font-medium text-ink-2">{label}</span>
      {Icon && <span className="hidden size-8 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent sm:grid"><Icon size={16} /></span>}
    </div>
    <div className={`mt-1 text-[26px] leading-tight font-semibold tracking-tight ${tone ?? ""}`}>{value}</div>
    <div className="mt-0.5 text-xs text-muted">{sub}</div>
  </div>
);

export const Meter = ({ value }) => (
  <div className="flex items-center justify-end gap-2.5">
    {value !== null && value !== undefined && <span className="h-1.5 w-16 overflow-hidden rounded-full bg-line @max-[800px]:hidden" aria-hidden="true"><span className="block h-full rounded-full bg-series" style={{ width: `${value * 100}%` }} /></span>}
    <span className="w-12 text-right tabular-nums">{pct(value)}</span>
  </div>
);

/** Histogram with hover/arrow-key readout. `median` draws a reference line. */
export function Hist({ values, lo, hi, step, median, ticks }) {
  const { counts, outside } = useMemo(() => {
    const c = new Array(Math.round((hi - lo) / step)).fill(0);
    let out = 0;
    for (const v of values) { if (v >= lo && v < hi) c[Math.min(c.length - 1, Math.floor((v - lo) / step))]++; else out++; }
    return { counts: c, outside: out };
  }, [values, lo, hi, step]);
  const [hover, setHover] = useState(null);
  const m = Math.max(1, ...counts);
  const at = (v) => `${((v - lo) / (hi - lo)) * 100}%`;
  const key = (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const d = e.key === "ArrowRight" ? 1 : -1;
    setHover((h) => Math.max(0, Math.min(counts.length - 1, h === null ? 0 : h + d)));
  };
  return (
    <div className="pl-11">
      <div className="relative h-52 pt-6" tabIndex={0} role="img" onKeyDown={key} onBlur={() => setHover(null)}
        aria-label={`Histogram of ${values.length} values from ${lo} to ${hi}, median ${median}. Use the arrow keys to read each bin.`}>
        <div className="absolute inset-x-0 top-6 bottom-0" aria-hidden="true">
          {[1, 0.5, 0].map((f) => (
            <div key={f} className={`absolute inset-x-0 border-t ${f ? "border-line" : "border-muted/50"}`} style={{ bottom: `${f * 100}%` }}>
              <span className="absolute right-full mr-2 -translate-y-1/2 text-[11px] text-muted tabular-nums">{Math.round(m * f).toLocaleString()}</span>
            </div>
          ))}
        </div>
        <div className="relative flex h-full items-end gap-0.5" onMouseLeave={() => setHover(null)}>
          {counts.map((x, i) => (
            <div key={i} className="flex h-full flex-1 items-end" onMouseEnter={() => setHover(i)}>
              <div className={`w-full rounded-t-[3px] transition-colors ${hover === i ? "bg-series-hover" : "bg-series"}`} style={{ height: x ? `max(2px, ${(x / m) * 100}%)` : 0 }} />
            </div>
          ))}
        </div>
        {median != null && (
          <div className="pointer-events-none absolute top-0 bottom-0" style={{ left: at(median) }}>
            <div className="absolute top-5 bottom-0 border-l-2 border-ink" />
            <span className="absolute top-0 -translate-x-1/2 text-[11.5px] font-semibold whitespace-nowrap">median {fmt(median)}</span>
          </div>
        )}
        {hover !== null && (
          <div className="pointer-events-none absolute top-7 z-10 -translate-x-1/2 rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs whitespace-nowrap text-white shadow-lg ring-1 ring-white/15"
            style={{ left: `clamp(70px, ${((hover + 0.5) / counts.length) * 100}%, calc(100% - 70px))` }}>
            {(lo + hover * step).toFixed(2)} to {(lo + (hover + 1) * step).toFixed(2)}: <b>{counts[hover].toLocaleString()}</b> rows
          </div>
        )}
      </div>
      <div className="relative mt-1.5 h-4 text-[11px] text-muted tabular-nums">
        {ticks.map((t) => <span key={t} className="absolute -translate-x-1/2" style={{ left: at(t) }}>{t.toFixed(1)}</span>)}
      </div>
      {outside > 0 && <p className="mt-1.5 text-xs text-muted">{outside.toLocaleString()} rows fall outside this axis and are not drawn.</p>}
    </div>
  );
}

export function Modal({ title, onClose, children }) {
  const close = useRef(null);
  const panel = useRef(null);
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    const before = document.activeElement;
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    close.current?.focus();
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; before?.focus?.(); };
  }, [onClose]);
  useEffect(() => { panel.current?.scrollTo(0, 0); }, [title]);
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-950/55 backdrop-blur-[2px]" onClick={onClose}>
      <div ref={panel} role="dialog" aria-modal="true" aria-label={`Record trail for ${title}`} onClick={(e) => e.stopPropagation()}
        className="drawer-in h-full w-full max-w-5xl overflow-y-auto bg-page shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-line bg-surface/90 px-5 py-3 backdrop-blur-md">
          <div className="min-w-0"><p className="text-xs font-medium text-muted">Record trail</p><p className="truncate font-mono text-[15px] font-semibold">{title}</p></div>
          <button ref={close} onClick={onClose} aria-label="Close" className="grid size-9 shrink-0 place-items-center rounded-lg border border-line bg-surface text-ink-2 hover:bg-raised pointer-coarse:size-11"><X size={17} /></button>
        </div>
        <div className="space-y-4 p-3 sm:space-y-5 sm:p-5">{children}</div>
      </div>
    </div>
  );
}

const longText = (v) => typeof v === "string" && v.length > 48;

function Cell({ col, value, onOpen }) {
  if (value === null || value === undefined || value === "") return <span className="text-muted">-</span>;
  if (typeof value === "string" && ENTITY.test(value)) {
    return onOpen
      ? <button onClick={() => onOpen(value)} className="font-mono text-[12px] font-medium text-accent hover:underline pointer-coarse:py-2">{value}</button>
      : <span className="font-mono text-[12px]">{value}</span>;
  }
  if (STATUS_COLUMNS.has(col)) return <Pill value={String(value)} />;
  return fmt(value);
}

/** Sortable table; ID cells become links when onOpen is given. */
export function DataTable({ rows, cols, onOpen, bare }) {
  const [sort, setSort] = useState(null);
  const columns = cols ?? Object.keys(rows[0] ?? {});
  const sorted = useMemo(() => {
    if (!sort) return rows;
    return [...rows].sort((a, b) => {
      const x = a[sort.c], y = b[sort.c];
      if (x === null) return 1;
      if (y === null) return -1;
      return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * sort.d;
    });
  }, [rows, sort]);
  if (!rows.length) return <p className={`text-[13px] text-muted ${bare ? "" : "px-5 pb-5"}`}>None.</p>;
  const numeric = (c) => rows.some((r) => typeof r[c] === "number") && rows.every((r) => r[c] === null || r[c] === undefined || typeof r[c] === "number");
  return (
    <>
      <div className={`@container max-h-[min(560px,70dvh)] overflow-auto border-t border-line ${bare ? "rounded-xl border" : "rounded-b-2xl"}`}>
        {rows.length > 1 && (
          <div className="stack-only sticky top-0 z-[2] items-center gap-2 border-b border-line bg-raised px-5 py-2 text-xs text-ink-2">
            <label className="flex min-w-0 flex-1 items-center gap-2">Sort by
              <select value={sort?.c ?? ""} onChange={(e) => setSort(e.target.value ? { c: e.target.value, d: sort?.d ?? 1 } : null)}
                className="h-8 min-w-0 flex-1 rounded-lg border border-line bg-surface px-2 text-[13px] pointer-coarse:h-11 pointer-coarse:text-base">
                <option value="">Default order</option>
                {columns.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <button disabled={!sort} onClick={() => setSort({ ...sort, d: -sort.d })} aria-label={sort?.d === -1 ? "Sorted descending, switch to ascending" : "Sorted ascending, switch to descending"}
              className="grid size-8 shrink-0 place-items-center rounded-lg border border-line bg-surface disabled:opacity-40 pointer-coarse:size-11">
              {sort?.d === -1 ? <ArrowDown size={14} /> : <ArrowUp size={14} />}
            </button>
          </div>
        )}
        <table className="stack-table w-full border-separate border-spacing-0 text-[12.5px]">
          <thead><tr>{columns.map((c) => {
            const on = sort?.c === c;
            const Icon = on ? (sort.d === 1 ? ArrowUp : ArrowDown) : ChevronsUpDown;
            return (
              <th key={c} scope="col" aria-sort={on ? (sort.d === 1 ? "ascending" : "descending") : "none"} className="sticky top-0 z-[1] border-b border-line bg-raised p-0 font-semibold first:left-0 first:z-[2] first:shadow-[1px_0_0_var(--line)] first:[&>button]:pl-5">
                <button onClick={() => setSort({ c, d: on ? -sort.d : 1 })} className={`flex w-full items-center gap-1 px-3.5 py-2.5 text-xs whitespace-nowrap text-ink-2 hover:text-ink ${numeric(c) ? "justify-end" : ""}`}>
                  {c}<Icon size={12} className={on ? "text-accent" : "text-muted/60"} />
                </button>
              </th>
            );
          })}</tr></thead>
          <tbody>{sorted.map((r, i) => (
            <tr key={i} className="group">{columns.map((c) => (
              <td key={c} data-label={c} className={`border-b border-line/70 px-3.5 py-2 first:sticky first:left-0 first:bg-surface first:pl-5 first:shadow-[1px_0_0_var(--line)] group-last:border-b-0 group-hover:bg-accent-soft/45 group-hover:first:bg-accent-soft ${numeric(c) ? "text-right tabular-nums" : ""} ${longText(r[c]) ? "min-w-72 max-w-xl" : "whitespace-nowrap"}`}>
                <Cell col={c} value={r[c]} onOpen={onOpen} />
              </td>
            ))}</tr>
          ))}</tbody>
        </table>
      </div>
    </>
  );
}
