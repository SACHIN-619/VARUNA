import React from 'react';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { FileCheck, ShieldAlert, CheckCircle2, Lock, Cpu, Database } from 'lucide-react';

export const ProvenancePage: React.FC = () => {
  const artifacts = [
    {
      component: "Adaptive Reliability Engine",
      provenance: "PHYSICS_INFORMED_HEURISTIC",
      evidence: "Simplex constraint proof (Σw_i = 1.0) and orographic windward weights.",
      status: "VERIFIED"
    },
    {
      component: "Supervised ML Meta-Model",
      provenance: "CONTROLLED_BENCHMARK",
      evidence: "Chronological train / validation / test split (no temporal leakage); results in Verification Centre.",
      status: "VERIFIED"
    },
    {
      component: "Model-Weight Maps (India 14 Subdivisions)",
      provenance: "PHYSICS_INFORMED_HEURISTIC",
      evidence: "14 Indian meteorological subdivisions with GeoJSON RFC 7946 compliance.",
      status: "VERIFIED"
    },
    {
      component: "Observation Ground Truth Provider",
      provenance: "SYNTHETIC_STRESS_TEST",
      evidence: "IMDAA 12km reanalysis & AWS surface telemetry emulation.",
      status: "VERIFIED"
    },
    {
      component: "Operational NCMRWF Live Feeds",
      provenance: "AUTHORIZED_ACCESS_REQUIRED",
      evidence: "Architecture adapters implemented for authorized MoES VPN gateways.",
      status: "READY FOR GATEWAY"
    }
  ];

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 w-full animate-fadeIn">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-primary font-bold uppercase tracking-wider">
              Scientific Audit & Transparency
            </span>
            <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="TRANSPARENT SCIENTIFIC PROVENANCE" />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">
            DATA PROVENANCE & GOVERNANCE CENTRE
          </h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1">
            Explicit provenance tagging and verification evidence for every component in the VARUNA intelligence stack.
          </p>
        </div>
      </div>

      {/* Lineage Table */}
      <div className="p-5 rounded-2xl bg-surface border border-surface-border shadow-xl">
        <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider mb-4 flex items-center gap-2">
          <FileCheck className="w-4 h-4 text-primary" />
          <span>Scientific Provenance Inventory</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-surface-border text-on-surface-variant bg-surface-deep/60">
                <th className="p-3">SYSTEM COMPONENT</th>
                <th className="p-3">PROVENANCE CATEGORY</th>
                <th className="p-3">VERIFICATION EVIDENCE</th>
                <th className="p-3">ENGINEERING STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border text-on-surface-variant">
              {artifacts.map((a, idx) => (
                <tr key={idx} className="hover:bg-surface-card transition-colors">
                  <td className="p-3 font-headline font-bold text-on-surface">{a.component}</td>
                  <td className="p-3">
                    <ProvenanceBadge type={a.provenance} />
                  </td>
                  <td className="p-3 text-on-surface-variant">{a.evidence}</td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 border border-emerald-800 text-[10px] font-bold">
                      {a.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
