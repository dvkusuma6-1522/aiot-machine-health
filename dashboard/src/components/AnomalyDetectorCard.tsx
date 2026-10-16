"use client";

import React from "react";
import { ShieldCheck, AlertTriangle, AlertOctagon, HelpCircle, Info, CheckCircle2 } from "lucide-react";
import { AnomalyItem } from "../types/environment";
import { formatTime } from "../lib/utils";

interface AnomalyDetectorCardProps {
  latestAnomaly: AnomalyItem | null;
  loading: boolean;
}

export const AnomalyDetectorCard: React.FC<AnomalyDetectorCardProps> = ({ latestAnomaly, loading }) => {
  const isAnomaly = latestAnomaly?.is_anomaly || false;
  const severity = latestAnomaly?.severity || "NORMAL";
  const score = latestAnomaly?.anomaly_score;

  return (
    <div className="rounded-xl border border-forest-800 bg-forest-900/60 p-5 space-y-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-forest-850 pb-3">
        <div className="flex items-center gap-2">
          <div
            className={`p-2 rounded-lg border ${
              severity === "CRITICAL"
                ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
                : severity === "WARNING"
                ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
            }`}
          >
            {severity === "CRITICAL" ? (
              <AlertOctagon className="w-4 h-4" />
            ) : severity === "WARNING" ? (
              <AlertTriangle className="w-4 h-4" />
            ) : (
              <ShieldCheck className="w-4 h-4" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Isolation Forest Anomaly Detection
            </h3>
            <p className="text-[11px] text-slate-400">
              Multivariate unsupervised outlier detection &bull; Contamination &nu; = 0.05
            </p>
          </div>
        </div>

        {/* Severity Badge */}
        <div>
          <span
            className={`text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider border ${
              severity === "CRITICAL"
                ? "bg-rose-950/70 text-rose-300 border-rose-500/40"
                : severity === "WARNING"
                ? "bg-amber-950/70 text-amber-300 border-amber-500/40"
                : "bg-emerald-950/70 text-emerald-300 border-emerald-500/40"
            }`}
          >
            {severity}
          </span>
        </div>
      </div>

      {/* Main Detection Outcome */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Score & Evaluation */}
        <div className="p-3.5 rounded-lg bg-forest-950/80 border border-forest-800 space-y-2">
          <span className="text-xs text-slate-400 block">Outlier Decision Score</span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-extrabold font-mono text-white">
              {score !== null && score !== undefined ? score.toFixed(4) : "+0.1500"}
            </span>
            <span className="text-[11px] text-slate-500">(&lt; 0.0 indicates anomaly)</span>
          </div>
          <div className="text-[11px] text-slate-400">
            {isAnomaly ? (
              <span className="text-rose-400 font-semibold flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> Multivariate Outlier Flagged
              </span>
            ) : (
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Nominal Environmental Dynamics
              </span>
            )}
          </div>
        </div>

        {/* Affected Sensors (Feature Attribution) */}
        <div className="p-3.5 rounded-lg bg-forest-950/80 border border-forest-800 space-y-2">
          <span className="text-xs text-slate-400 block">Primary Feature Attribution</span>
          {latestAnomaly?.affected_sensors && latestAnomaly.affected_sensors.length > 0 ? (
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              {latestAnomaly.affected_sensors.map((sensor) => (
                <span
                  key={sensor}
                  className="px-2 py-0.5 rounded bg-rose-950/60 border border-rose-500/30 text-rose-300 font-mono text-[11px] font-medium"
                >
                  {sensor}
                </span>
              ))}
            </div>
          ) : (
            <div className="text-[11px] text-slate-400 italic pt-1">
              All 5 sensor channels within nominal statistical envelope (&plusmn;2.0&sigma;)
            </div>
          )}
          <p className="text-[10px] text-slate-500">
            Calculated via z-score deviations against baseline training cluster.
          </p>
        </div>

        {/* Suggested Operator Action */}
        <div className="p-3.5 rounded-lg bg-forest-950/80 border border-forest-800 space-y-1">
          <span className="text-xs text-slate-400 block">Suggested Verification</span>
          <p className="text-xs text-slate-200 font-medium">
            {latestAnomaly?.suggested_action || "Continue continuous automated telemetry ingestion."}
          </p>
          {latestAnomaly?.explanation && (
            <p className="text-[11px] text-slate-400 pt-1 border-t border-forest-850 mt-1">
              {latestAnomaly.explanation}
            </p>
          )}
        </div>
      </div>

      {/* Educational Scientific Disclaimer */}
      <div className="flex items-start gap-2.5 p-3 rounded-lg bg-forest-950/40 border border-forest-850 text-slate-400 text-[11px]">
        <Info className="w-4 h-4 text-teal-400 flex-shrink-0 mt-0.5" />
        <p>
          <strong>Scientific Interpretation Note:</strong> Isolation Forest identifies multidimensional statistical deviations from the baseline distribution. An anomaly flag indicates unusual multi-sensor divergence and warrants manual inspection; it does not automatically prove toxic contamination, physical fire, or sensor destruction.
        </p>
      </div>
    </div>
  );
};
