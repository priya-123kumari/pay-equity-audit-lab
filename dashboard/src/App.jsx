import { useEffect, useMemo, useState } from "react";
import { FileSearch, HandCoins, LayoutDashboard, LoaderCircle, Moon, Scale, Search, ShieldCheck, Sun, TriangleAlert } from "lucide-react";
import { makeLookup, useData } from "./data.js";
import { Modal } from "./ui.jsx";
import { Trace } from "./Trace.jsx";
import { Anomalies, Gaps, Overview, Validation } from "./tabs.jsx";

const TABS = [
  { id: "overview", label: "Overview", short: "Overview", icon: LayoutDashboard, about: "Audit verdict, detection quality and dataset shape" },
  { id: "validation", label: "Validation", short: "Validation", icon: ShieldCheck, about: "Every rule-based check and what it found" },
  { id: "anomalies", label: "Anomalies vs ground truth", short: "Anomalies", icon: FileSearch, about: "Planted issues, traceable to the records behind them" },
  { id: "gaps", label: "Pay gaps & proposals", short: "Pay gaps", icon: HandCoins, about: "Flagged employees, exceptions and adjustment proposals" },
];

const tabFromHash = () => TABS.find((t) => `#${t.id}` === window.location.hash) ?? TABS[0];

function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  const toggle = () => {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    try { localStorage.setItem("theme", next ? "dark" : "light"); } catch { /* storage blocked: theme lasts for this visit */ }
    setDark(next);
  };
  return [dark, toggle];
}

const Brand = () => (
  <div className="flex items-center gap-3">
    <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 text-white shadow-lg shadow-blue-950/40"><Scale size={19} /></span>
    <span className="leading-tight text-white"><b className="block text-[15px] font-semibold">Pay Equity Audit Lab</b><span className="text-xs text-slate-400">Review Dashboard</span></span>
  </div>
);

export default function App() {
  const { data, error } = useData();
  const [tab, setTab] = useState(tabFromHash);
  const [trace, setTrace] = useState(null);
  const [q, setQ] = useState("");
  const [dark, toggleTheme] = useTheme();
  const get = useMemo(() => (data ? makeLookup(data.tables) : null), [data]);

  useEffect(() => {
    const sync = () => setTab(tabFromHash());
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  if (error) {
    return (
      <main className="mx-auto mt-[12vh] max-w-2xl px-4">
        <div className="rounded-2xl border border-line bg-surface p-8 shadow-sm">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-bad"><TriangleAlert size={20} />Could not load the data</h2>
          <p className="mt-2 break-words text-ink-2">{error}</p>
          <p className="mt-4 text-ink-2">Generate and sync it: <code className="rounded bg-raised px-1.5 py-0.5">python -m generator --seed 20261022 --employees 5000 --out data/full</code>, then <code className="rounded bg-raised px-1.5 py-0.5">npm run sync-data</code>. Serve over http with <code className="rounded bg-raised px-1.5 py-0.5">npm run dev</code>; opening index.html as a file will not work.</p>
        </div>
      </main>
    );
  }
  if (!data) return <main className="grid min-h-screen place-items-center text-muted"><p className="flex items-center gap-2"><LoaderCircle className="animate-spin" size={18} />Loading data...</p></main>;

  const submit = (e) => { e.preventDefault(); if (q.trim()) setTrace(q.trim()); };
  const go = (t) => { window.location.hash = t.id; setTab(t); window.scrollTo(0, 0); };
  const { distributions: d } = data.metrics;

  return (
    <div className="min-h-screen lg:pl-64">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col overflow-y-auto bg-navy p-4 lg:flex">
        <div className="px-2 py-2"><Brand /></div>
        <nav className="mt-7 flex flex-col gap-1" aria-label="Sections">
          {TABS.map((t) => (
            <button key={t.id} aria-current={t === tab ? "page" : undefined} onClick={() => go(t)}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13.5px] font-medium transition-colors focus-visible:outline-white ${t === tab ? "bg-white/12 text-white" : "text-slate-300 hover:bg-white/6 hover:text-white"}`}>
              <t.icon size={17} className={`shrink-0 ${t === tab ? "text-sky-300" : "text-slate-400"}`} />{t.label}
            </button>
          ))}
        </nav>
        <dl className="mt-auto grid shrink-0 grid-cols-2 gap-y-3 rounded-xl border border-white/10 bg-white/5 p-3.5 text-xs">
          <div><dt className="text-slate-400">Employees</dt><dd className="mt-0.5 font-semibold text-white">{d.employees.toLocaleString()}</dd></div>
          <div><dt className="text-slate-400">Seed</dt><dd className="mt-0.5 font-semibold text-white">{data.manifest.seed}</dd></div>
          <div className="col-span-2"><dt className="text-slate-400">Data</dt><dd className="mt-0.5 font-semibold text-white">Synthetic, reproducible</dd></div>
        </dl>
      </aside>

      <header className="z-20 border-b lg:sticky lg:top-0 border-line bg-surface/85 backdrop-blur-md">
        <div className="bg-navy px-4 py-3 lg:hidden"><Brand /></div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2.5 px-4 py-3 sm:px-6 lg:px-8">
          <div className="min-w-0 flex-1 basis-56">
            <h1 className="truncate text-[17px] font-semibold tracking-tight">{tab.label}</h1>
            <p className="text-xs text-muted sm:truncate">{tab.about}</p>
          </div>
          <form onSubmit={submit} role="search" className="relative order-last w-full sm:order-none sm:w-80 xl:w-96">
            <Search size={15} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted" />
            <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="Look up a record by ID" placeholder="Look up EMP-000123, ADJ-..., CRS-..., CG-..."
              className="h-9 w-full rounded-lg border border-line bg-raised pr-3 pl-9 text-[13px] text-ellipsis placeholder:text-muted pointer-coarse:h-11 pointer-coarse:text-base" />
          </form>
          <button onClick={toggleTheme} aria-label={dark ? "Switch to light mode" : "Switch to dark mode"} title={dark ? "Light mode" : "Dark mode"}
            className="grid size-9 place-items-center rounded-lg border border-line bg-surface text-ink-2 transition-colors hover:bg-raised pointer-coarse:size-11">
            {dark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
        <nav className="hidden gap-1 overflow-x-auto px-3 pb-2 sm:flex lg:hidden" aria-label="Sections">
          {TABS.map((t) => (
            <button key={t.id} aria-current={t === tab ? "page" : undefined} onClick={() => go(t)}
              className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] font-medium ${t === tab ? "bg-accent-soft text-accent" : "text-ink-2"}`}>
              <t.icon size={15} />{t.label}
            </button>
          ))}
        </nav>
      </header>

      <main key={tab.id} className="fade-up mx-auto max-w-[1400px] space-y-4 px-4 py-4 max-sm:pb-24 sm:space-y-6 sm:px-6 sm:py-6 lg:px-8">
        {tab.id === "overview" && <Overview data={data} />}
        {tab.id === "validation" && <Validation data={data} />}
        {tab.id === "anomalies" && <Anomalies data={data} onOpen={setTrace} />}
        {tab.id === "gaps" && <Gaps data={data} onOpen={setTrace} />}
      </main>
      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] sm:hidden" aria-label="Sections">
        {TABS.map((t) => (
          <button key={t.id} aria-current={t === tab ? "page" : undefined} onClick={() => go(t)}
            className={`flex min-h-14 min-w-0 flex-col items-center justify-center gap-0.5 text-[11.5px] font-medium ${t === tab ? "text-accent" : "text-ink-2"}`}>
            <t.icon size={18} />{t.short}
          </button>
        ))}
      </nav>
      {trace && <Modal title={trace} onClose={() => setTrace(null)}><Trace id={trace} data={data} get={get} onOpen={setTrace} /></Modal>}
    </div>
  );
}
