import React from 'react';
import { ProvenanceBadge } from '../components/shared/ProvenanceBadge';
import { Code, ExternalLink, Database, Server, CheckCircle2, Copy } from 'lucide-react';

export const ApiDocsPage: React.FC = () => {
  const endpoints = [
    {
      method: "GET",
      path: "/api/dashboard/summary",
      desc: "Unified overview endpoint powering the main Meteorological Control Room.",
      params: "region_id, variable, lead_hours, weather_regime"
    },
    {
      method: "GET",
      path: "/api/fusion/weight-map",
      desc: "Returns 14 Indian subdivisions GeoJSON RFC 7946 with normalized trust weights.",
      params: "variable, lead_hours, season, weather_regime, strategy"
    },
    {
      method: "GET",
      path: "/api/fusion/trace",
      desc: "Decomposes XAI attribution into regional skill, recent verification, and regime penalties.",
      params: "region_id, variable, lead_hours, weather_regime"
    },
    {
      method: "GET",
      path: "/api/verification/summary",
      desc: "Continuous empirical benchmark evaluating MAE, RMSE, and bias across all models.",
      params: "variable"
    },
    {
      method: "GET",
      path: "/api/v1/forecast/fused",
      desc: "Canonical REST endpoint returning fused prediction with disagreement & confidence.",
      params: "region_id, variable, lead_hours, weather_regime"
    },
    {
      method: "POST",
      path: "/api/demo/inject-failure",
      desc: "Simulates operational failure modes: model dropout, wet-bias injection, or forced disagreement.",
      params: "action, model_id, bias_magnitude"
    }
  ];

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 w-full animate-fadeIn">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-primary font-bold uppercase tracking-wider">
              Developer & Gateway Integration
            </span>
            <ProvenanceBadge type="CONTROLLED_BENCHMARK" label="FASTAPI OPENAPI SPECIFICATION" />
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-on-surface tracking-tight">
            VARUNA REST API EXPLORER
          </h1>
          <p className="text-xs font-mono text-on-surface-variant mt-1">
            Structured JSON endpoints conforming to the SIH26081 Frontend Control Room Contract.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href="/api/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-headline font-bold text-xs uppercase tracking-wide flex items-center gap-2 transition-all shadow-glow-cyan/20"
          >
            <span>Open Interactive Swagger Docs</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Endpoints List */}
      <div className="p-5 rounded-2xl bg-surface border border-surface-border shadow-xl space-y-3">
        <h3 className="font-headline font-bold text-sm text-on-surface uppercase tracking-wider mb-2 flex items-center gap-2">
          <Code className="w-4 h-4 text-primary" />
          <span>Core API Endpoints</span>
        </h3>

        <div className="divide-y divide-surface-border">
          {endpoints.map((ep, i) => (
            <div key={i} className="p-3.5 hover:bg-surface-card transition-colors flex flex-col gap-1.5">
              <div className="flex items-center gap-2 font-mono text-xs">
                <span className={`px-2 py-0.5 rounded font-extrabold ${ep.method === 'GET' ? 'bg-cyan-50 dark:bg-cyan-950 text-primary border border-cyan-800' : 'bg-purple-50 dark:bg-purple-950 text-purple-600 dark:text-purple-400 border border-purple-800'}`}>
                  {ep.method}
                </span>
                <span className="font-bold text-on-surface">{ep.path}</span>
              </div>
              <p className="text-xs font-sans text-on-surface-variant">{ep.desc}</p>
              <div className="text-[11px] font-mono text-on-surface-variant">
                Parameters: <code className="text-on-surface-variant bg-surface-deep px-1.5 py-0.2 rounded border border-surface-border">{ep.params}</code>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
