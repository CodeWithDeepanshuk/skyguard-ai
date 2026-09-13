'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Archive, CheckCircle2, FileSearch, FlaskConical, Search, ShieldCheck, X } from 'lucide-react';

type EvidenceStatus = 'RECORDED_PASS' | 'RECORDED_RESULT' | 'LIMITATION' | 'EXCLUDED' | 'UNAVAILABLE';

interface EvidenceItem {
  key: string;
  name: string;
  category: string;
  status: EvidenceStatus;
  measured_value: string;
  scope: string;
  description: string;
  artifact: string | null;
}

interface EvidenceResponse {
  title: string;
  model_version: string | null;
  claim_scope: string;
  summary: Record<string, number>;
  evidence: EvidenceItem[];
}

const statusStyle: Record<EvidenceStatus, { label: string; className: string }> = {
  RECORDED_PASS: { label: 'Recorded pass', className: 'border-emerald-200 bg-emerald-50 text-emerald-800' },
  RECORDED_RESULT: { label: 'Recorded result', className: 'border-sky-200 bg-sky-50 text-sky-800' },
  LIMITATION: { label: 'Open limitation', className: 'border-amber-200 bg-amber-50 text-amber-900' },
  EXCLUDED: { label: 'Excluded claim', className: 'border-rose-200 bg-rose-50 text-rose-800' },
  UNAVAILABLE: { label: 'Unavailable', className: 'border-slate-200 bg-slate-100 text-slate-700' },
};

export default function ScientificEvidencePage() {
  const [data, setData] = useState<EvidenceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('ALL');
  const [selected, setSelected] = useState<EvidenceItem | null>(null);

  useEffect(() => {
    fetch('/api/gates', { cache: 'no-store' })
      .then(async response => {
        if (!response.ok) throw new Error('Scientific evidence is temporarily unavailable.');
        return response.json();
      })
      .then(setData)
      .catch(reason => setError(reason instanceof Error ? reason.message : 'Evidence unavailable.'));
  }, []);

  const categories = useMemo(
    () => Array.from(new Set((data?.evidence || []).map(item => item.category))),
    [data],
  );
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (data?.evidence || []).filter(item => {
      const matchesCategory = category === 'ALL' || item.category === category;
      const matchesQuery = !needle || [item.key, item.name, item.description, item.measured_value]
        .some(value => value.toLowerCase().includes(needle));
      return matchesCategory && matchesQuery;
    });
  }, [category, data, query]);

  return (
    <main className="min-h-full space-y-5 bg-[#F5F9FC] p-4 font-sans sm:p-6">
      <section className="overflow-hidden rounded-3xl border border-[#D8E6EF] bg-white/90 p-6 shadow-[0_20px_70px_-40px_rgba(23,105,170,.45)] backdrop-blur-xl">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div className="max-w-3xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[10px] font-bold uppercase tracking-[.18em] text-[#1769AA]">
              <ShieldCheck className="h-3.5 w-3.5" /> Scientific evidence
            </div>
            <h1 className="text-3xl font-black tracking-tight text-[#102A43] sm:text-4xl">Evidence before promotion.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[#52667A]">
              This register separates reproducible offline results from live operational claims. A recorded pass means the named repository validation produced that result; it is not an IMD deployment certificate.
            </p>
          </div>
          <div className="grid min-w-[260px] grid-cols-2 gap-2 text-xs">
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-emerald-700">Recorded checks</span>
              <strong className="mt-1 block text-2xl text-emerald-900">{(data?.summary.RECORDED_PASS || 0) + (data?.summary.RECORDED_RESULT || 0)}</strong>
            </div>
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-amber-700">Visible limits</span>
              <strong className="mt-1 block text-2xl text-amber-900">{data?.summary.LIMITATION || 0}</strong>
            </div>
          </div>
        </div>
        <div className="mt-5 flex flex-wrap gap-2 border-t border-slate-100 pt-4 text-[11px] text-slate-600">
          <span className="rounded-full bg-slate-100 px-3 py-1 font-mono">Model: {data?.model_version || 'Not available'}</span>
          <span className="rounded-full bg-violet-50 px-3 py-1 text-violet-800">Offline research baseline</span>
          <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-900">Live field labels unavailable</span>
        </div>
      </section>

      <section className="rounded-2xl border border-[#D8E6EF] bg-white p-3 shadow-sm">
        <div className="grid gap-3 md:grid-cols-[1fr_280px]">
          <label className="relative">
            <Search className="absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
            <span className="sr-only">Search evidence</span>
            <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search artifact, metric or check" className="min-h-11 w-full rounded-xl border border-slate-200 bg-slate-50 pl-10 pr-3 text-sm text-[#102A43] outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100" />
          </label>
          <label>
            <span className="sr-only">Filter by evidence category</span>
            <select value={category} onChange={event => setCategory(event.target.value)} className="min-h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm text-[#102A43] outline-none focus:border-sky-500">
              <option value="ALL">All evidence categories</option>
              {categories.map(item => <option key={item}>{item}</option>)}
            </select>
          </label>
        </div>
      </section>

      {error && <div role="alert" className="flex items-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><AlertTriangle className="h-4 w-4" />{error}</div>}
      {!data && !error && <div className="rounded-2xl border border-[#D8E6EF] bg-white p-10 text-center text-sm text-[#52667A]">Loading repository evidence…</div>}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map(item => {
          const style = statusStyle[item.status];
          return (
            <button key={item.key} onClick={() => setSelected(item)} className="group min-h-56 rounded-2xl border border-[#D8E6EF] bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-sky-300 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500">
              <div className="flex items-start justify-between gap-3">
                <span className="font-mono text-[10px] font-bold tracking-wide text-[#1769AA]">{item.key}</span>
                <span className={`rounded-full border px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider ${style.className}`}>{style.label}</span>
              </div>
              <h2 className="mt-4 text-base font-extrabold text-[#102A43] group-hover:text-[#1769AA]">{item.name}</h2>
              <p className="mt-2 text-xs leading-5 text-[#52667A]">{item.description}</p>
              <div className="mt-4 border-t border-slate-100 pt-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Measured or recorded</p>
                <p className="mt-1 text-xs font-semibold leading-5 text-slate-800">{item.measured_value}</p>
              </div>
            </button>
          );
        })}
      </section>

      {data && filtered.length === 0 && <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">No evidence item matches this filter.</div>}

      {selected && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/20 backdrop-blur-sm" onMouseDown={event => { if (event.currentTarget === event.target) setSelected(null); }}>
          <aside className="h-full w-full max-w-lg overflow-y-auto border-l border-[#D8E6EF] bg-white p-6 shadow-2xl" aria-label="Evidence detail">
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className={`inline-flex rounded-full border px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider ${statusStyle[selected.status].className}`}>{statusStyle[selected.status].label}</span>
                <h2 className="mt-3 text-2xl font-black text-[#102A43]">{selected.name}</h2>
              </div>
              <button onClick={() => setSelected(null)} aria-label="Close evidence detail" className="grid min-h-11 min-w-11 place-items-center rounded-xl text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button>
            </div>
            <dl className="mt-7 space-y-5 text-sm">
              <div className="rounded-2xl bg-[#EDF6FB] p-4"><dt className="text-[10px] font-bold uppercase tracking-wider text-[#1769AA]">Scope</dt><dd className="mt-1 font-semibold text-[#102A43]">{selected.scope}</dd></div>
              <div><dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Recorded result</dt><dd className="mt-1 leading-6 text-slate-800">{selected.measured_value}</dd></div>
              <div><dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Interpretation</dt><dd className="mt-1 leading-6 text-[#52667A]">{selected.description}</dd></div>
              <div><dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Repository artifact</dt><dd className="mt-1 break-all rounded-xl border border-slate-200 bg-slate-50 p-3 font-mono text-xs text-slate-700">{selected.artifact || 'No artifact — explicitly documented limitation'}</dd></div>
            </dl>
            <div className="mt-8 rounded-2xl border border-violet-200 bg-violet-50 p-4 text-xs leading-5 text-violet-900">
              <FlaskConical className="mr-2 inline h-4 w-4" /> Research evidence supports engineering decisions; independent live maintenance labels are still required for field certification.
            </div>
          </aside>
        </div>
      )}

      <footer className="flex flex-col gap-2 rounded-2xl border border-[#D8E6EF] bg-white p-4 text-xs text-[#52667A] sm:flex-row sm:items-center sm:justify-between">
        <span className="flex items-center gap-2"><Archive className="h-4 w-4 text-[#1769AA]" />Candidate artifacts stay preserved even when their public claims are excluded.</span>
        <span className="flex items-center gap-2"><FileSearch className="h-4 w-4 text-[#0F9D8A]" />Every visible result names its evidence scope.</span>
      </footer>
    </main>
  );
}
