'use client';

import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  ShieldAlert, 
  Search, 
  Filter, 
  Info,
  CheckCheck
} from 'lucide-react';

interface Gate {
  key: string;
  name: string;
  category: string;
  threshold: string;
  actual_status: boolean;
  status_label: 'PASS' | 'FAIL';
  description: string;
}

export default function ValidationPage() {
  const [gates, setGates] = useState<Gate[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pass' | 'fail'>('all');
  const [categoryFilter, setCategoryFilter] = useState('all');

  useEffect(() => {
    fetch('/api/gates')
      .then(res => res.json())
      .then(data => {
        setGates(data.gates || []);
        setSummary(data.summary || null);
        setLoading(false);
      })
      .catch(() => {
        setGates([]);
        setSummary(null);
        setLoading(false);
      });
  }, []);

  const filtered = gates.filter(g => {
    const matchesStatus = filter === 'all' || 
      (filter === 'pass' && g.actual_status) || 
      (filter === 'fail' && !g.actual_status);
    const matchesCategory = categoryFilter === 'all' || g.category === categoryFilter;
    return matchesStatus && matchesCategory;
  });

  const categories = Array.from(new Set(gates.map(g => g.category)));

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="border-b border-[#1a4163] pb-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-purple-950 text-purple-400 border border-purple-800 text-xs font-semibold mb-2">
            <CheckCheck className="w-3.5 h-3.5" />
            <span>Strict Promotion Gatekeeper · No Hardcoded Outputs</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white flex items-center gap-2.5">
            25-Gate Operational Evaluation Pipeline
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            In SkyGuard AI, no model candidate is ever promoted automatically. Every model version must satisfy 25 predeclared mathematical constraints covering data leakage, recall across 18 fault modes, false alarms, and calibration ECE.
          </p>
        </div>

        {summary && (
          <div className="bg-[#0c2234] border border-[#1a4163] rounded-2xl p-5 shadow-xl flex items-center space-x-6">
            <div className="text-center">
              <span className="text-xs uppercase font-bold text-slate-400">Passed Gates</span>
              <div className="text-3xl sm:text-4xl font-black text-white mt-1">
                <span className="text-emerald-400">{summary.passed_gates}</span> / {summary.total_gates}
              </div>
            </div>
            <div className="h-10 w-px bg-[#1a4163]"></div>
            <div>
              <span className="text-xs text-slate-400 block font-semibold">Promotion Status</span>
              <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-bold border mt-1 ${
                summary.passed_gates === summary.total_gates
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                  : 'bg-amber-950 text-amber-300 border-amber-800'
              }`}>
                {summary.passed_gates === summary.total_gates ? 'Production Promoted' : 'Shadow Deployment'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#0c2234] border border-[#1a4163] p-3.5 rounded-xl">
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
              filter === 'all' ? 'bg-cyan-600 text-white' : 'bg-[#071521] text-slate-300 hover:bg-[#143652]'
            }`}
          >
            All Gates ({gates.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('pass')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
              filter === 'pass' ? 'bg-emerald-600 text-white' : 'bg-[#071521] text-slate-300 hover:bg-[#143652]'
            }`}
          >
            Passed ({gates.filter(g => g.actual_status).length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('fail')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
              filter === 'fail' ? 'bg-rose-600 text-white' : 'bg-[#071521] text-slate-300 hover:bg-[#143652]'
            }`}
          >
            Failed / Research Frontier ({gates.filter(g => !g.actual_status).length})
          </button>
        </div>

        <div>
          <select
            value={categoryFilter}
            onChange={e => setCategoryFilter(e.target.value)}
            className="bg-[#071521] border border-[#1a4163] rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Categories</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Gates Table */}
      <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-16 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
            <div className="w-6 h-6 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
            <span>Evaluating gate constraints...</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-[#071521] text-xs uppercase text-slate-400 font-semibold border-b border-[#1a4163]">
                <tr>
                  <th className="px-4 py-3">Gate Name</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Strict Threshold</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Scientific Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1a4163]/50">
                {filtered.map(gate => (
                  <tr key={gate.key} className="hover:bg-[#143652]/30 transition-colors">
                    <td className="px-4 py-3.5 font-bold text-white font-mono text-xs">
                      {gate.name}
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400">
                      <span className="px-2 py-0.5 rounded bg-[#071521] border border-slate-800">
                        {gate.category}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-xs font-mono text-slate-300">
                      {gate.threshold}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-black uppercase ${
                        gate.actual_status
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : 'bg-rose-950 text-rose-400 border border-rose-800'
                      }`}>
                        {gate.actual_status ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>PASS</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3.5 h-3.5" />
                            <span>FAIL</span>
                          </>
                        )}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400 max-w-md">
                      {gate.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
