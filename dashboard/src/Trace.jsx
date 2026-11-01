import { CircleCheck, CircleX } from "lucide-react";
import { num, str } from "./data.js";
import { Card, DataTable, fmt } from "./ui.jsx";

const Sec = ({ t, children }) => <Card title={t}>{children}</Card>;
const Checks = ({ children }) => <div className="mt-3 space-y-1.5 rounded-xl border border-line bg-raised p-3.5 text-[13px]">{children}</div>;
const Check = ({ ok, children }) => (
  <div className={`flex items-start gap-2 ${ok ? "text-good" : "text-bad"}`}>
    {ok ? <CircleCheck size={15} className="mt-0.5 shrink-0" aria-label="Pass" /> : <CircleX size={15} className="mt-0.5 shrink-0" aria-label="Fail" />}
    <span className="min-w-0 break-words">{children}</span>
  </div>
);
const NoMatch = ({ id }) => <p className="font-medium text-bad">No match for "{id}"</p>;

export function Trace({ id, data, get, onOpen }) {
  if (id.startsWith("CG-")) return <GroupTrace id={id} get={get} onOpen={onOpen} />;
  let emp = null;
  if (/^EMP-\d{6}$/.test(id)) emp = id;
  else if (/^(CRS|SAL)-EMP-\d{6}/.test(id)) emp = id.slice(4, 14);
  else if (id.startsWith("ADJ-")) emp = str(get("AdjustmentProposal", "proposal_id", id)[0]?.employee_id) || null;
  if (!emp || get("Employee", "employee_id", emp).length === 0) return <NoMatch id={id} />;
  return <EmployeeTrace emp={emp} data={data} get={get} onOpen={onOpen} />;
}

function EmployeeTrace({ emp, data, get, onOpen }) {
  const t = (name) => get(name, "employee_id", emp);
  const sal = [...t("SalaryRecord")]
    .sort((a, b) => str(a.effective_from).localeCompare(str(b.effective_from)))
    .map((s) => ({ ...s, fte_equivalent_salary: Math.round((num(s.base_salary) / num(s.fte)) * 100) / 100 }));
  const snaps = t("CompaRatioSnapshot");
  const proposals = t("AdjustmentProposal");
  const groups = t("ComparableGroupMember").map((m) => get("ComparableGroup", "group_id", m.group_id)[0]).filter(Boolean);
  const ids = new Set([emp, ...snaps.map((s) => s.snapshot_id), ...proposals.map((p) => p.proposal_id)]);
  return (
    <>
      <h2 className="font-mono text-xl font-semibold tracking-tight">{emp}</h2>
      <Sec t="Employee"><DataTable bare rows={t("Employee")} /></Sec>
      <Sec t="Tenure (derived)"><DataTable bare rows={t("Tenure")} /></Sec>
      <Sec t="Salary history (append-only, effective-dated)">
        <DataTable bare rows={sal} cols={["salary_id", "effective_from", "effective_to", "role_id", "level_id", "location_id", "band_id", "currency", "fte", "base_salary", "fte_equivalent_salary", "change_reason", "promotion_id", "adjustment_id"]} />
      </Sec>
      <Sec t="Documented factors (performance evidence)"><DataTable bare rows={t("PerformanceEvidence")} cols={["evidence_id", "evidence_type", "cycle_year", "rating", "pay_factor_pct", "effective_from", "document_ref"]} /></Sec>
      {t("Promotion").length > 0 && <Sec t="Promotions"><DataTable bare rows={t("Promotion")} /></Sec>}
      {snaps.map((s) => {
        const b = get("CompensationBand", "band_id", s.band_id_used)[0];
        const recomputed = num(s.normalized_salary_usd) / num(s.band_mid_usd);
        return (
          <Sec key={s.snapshot_id} t={`Compa-ratio snapshot ${s.snapshot_id}`}>
            <DataTable bare rows={[s]} />
            <Checks>
              <Check ok={!!b && str(b.effective_from) <= str(s.snapshot_date) && str(s.snapshot_date) <= str(b.effective_to)}>
                Band used <b>{s.band_id_used}</b> is effective on {s.snapshot_date} ({str(b?.effective_from)} to {str(b?.effective_to)})
              </Check>
              <Check ok={num(s.fte) >= 1 || num(s.fte_applied) === 1}>FTE normalisation applied (fte={fmt(s.fte)})</Check>
              <Check ok={s.salary_currency === "USD" || num(s.fx_applied) === 1}>Currency converted to USD ({s.salary_currency})</Check>
              <Check ok={Math.abs(recomputed - num(s.compa_ratio)) < 1e-3}>compa_ratio = normalized / band_mid = {fmt(recomputed)}</Check>
            </Checks>
          </Sec>
        );
      })}
      <Sec t="Analysis result"><DataTable bare rows={t("PayGapAnalysis")} /></Sec>
      {proposals.map((p) => (
        <Sec key={p.proposal_id} t={`Proposal ${p.proposal_id}`}>
          <DataTable bare rows={[p]} />
          <h3 className="mt-4 mb-2 text-[13px] font-semibold">Approval trail</h3>
          <DataTable bare rows={[...get("ApprovalEvent", "proposal_id", p.proposal_id)].sort((a, b) => num(a.event_seq) - num(b.event_seq))}
            cols={["event_id", "event_seq", "from_status", "to_status", "event_date", "actor_role", "actor_id", "comment"]} />
        </Sec>
      ))}
      <Sec t="Comparable groups (N:M via bridge table)"><DataTable bare rows={groups} cols={["group_id", "grouping_basis", "member_count", "min_size_met", "rationale"]} onOpen={onOpen} /></Sec>
      <Sec t="Ground-truth labels for this employee"><DataTable bare rows={data.tables.GroundTruth.filter((g) => ids.has(g.entity_id))} /></Sec>
    </>
  );
}

function GroupTrace({ id, get, onOpen }) {
  const g = get("ComparableGroup", "group_id", id)[0];
  if (!g) return <NoMatch id={id} />;
  const members = get("ComparableGroupMember", "group_id", id).map((m) => ({ ...m, role_family: get("Role", "role_id", m.role_id)[0]?.role_family ?? null }));
  const fams = new Set(members.map((m) => str(m.role_family)));
  return (
    <>
      <h2 className="font-mono text-xl font-semibold tracking-tight break-all">{id}</h2>
      <Sec t="Comparable group">
        <DataTable bare rows={[g]} />
        <Checks>
          <Check ok={!(fams.size > 1 && !g.rationale)}>Role families: {[...fams].join(", ")}; rationale {g.rationale ? "present" : "MISSING"}</Check>
          <Check ok={members.length === num(g.member_count)}>member_count matches bridge rows ({members.length})</Check>
        </Checks>
      </Sec>
      <Sec t="Members"><DataTable bare rows={members} onOpen={onOpen} /></Sec>
    </>
  );
}
