"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  AlertOctagon,
  Bell,
  CheckCircle2,
  Filter,
  Cloud,
  CloudOff,
  Send,
  Loader2,
  Layers,
} from "lucide-react";
import { AnomalyItem, AlertRecord } from "../types/environment";

interface AlertHistoryListProps {
  alerts: AlertRecord[];
  anomalies: AnomalyItem[];
  loading: boolean;
  onTriggerTestAlert?: () => Promise<void>;
  isTestingAlert?: boolean;
}

export const AlertHistoryList: React.FC<AlertHistoryListProps> = ({
  alerts,
  anomalies,
  loading,
  onTriggerTestAlert,
  isTestingAlert = false,
}) => {
  const [activeTab, setActiveTab] = useState<"ALERTS" | "ANOMALIES">("ALERTS");
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");

  const filteredAlerts = alerts.filter((a) => {
    if (filterSeverity === "ALL") return true;
    return a.severity === filterSeverity;
  });

  const filteredAnomalies = anomalies.filter((a) => {
    if (filterSeverity === "ALL") return true;
    return a.severity === filterSeverity;
  });

  return (
    <div className="rounded-xl border border-forest-800 bg-forest-900/60 p-5 space-y-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-forest-850 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
            <Bell className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Alerts &amp; Environmental Incidents Log
            </h3>
            <p className="text-[11px] text-slate-400">
              Audit trail of threshold events, Blynk notifications, and AI outliers
            </p>
          </div>
        </div>

        {/* Right Controls: Tabs, Filter, Test Trigger */}
        <div className="flex flex-wrap items-center gap-2">
          {/* View Tab Selector */}
          <div className="flex items-center bg-forest-950 rounded-lg p-1 border border-forest-800 text-xs">
            <button
              onClick={() => setActiveTab("ALERTS")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                activeTab === "ALERTS"
                  ? "bg-teal-600/30 text-teal-300 font-bold border border-teal-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Thresholds ({alerts.length})
            </button>
            <button
              onClick={() => setActiveTab("ANOMALIES")}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                activeTab === "ANOMALIES"
                  ? "bg-teal-600/30 text-teal-300 font-bold border border-teal-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              AI Outliers ({anomalies.length})
            </button>
          </div>

          {/* Severity Filter */}
          <div className="flex items-center gap-1 bg-forest-950 rounded-lg p-1 border border-forest-800 text-xs">
            <Filter className="w-3 h-3 text-slate-400 ml-1" />
            {["ALL", "CRITICAL", "WARNING"].map((sev) => (
              <button
                key={sev}
                onClick={() => setFilterSeverity(sev)}
                className={`px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors ${
                  filterSeverity === sev
                    ? "bg-forest-800 text-teal-300 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {sev}
              </button>
            ))}
          </div>

          {/* Test Alert Dispatch Button */}
          {onTriggerTestAlert && (
            <button
              onClick={onTriggerTestAlert}
              disabled={isTestingAlert || loading}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-teal-500/40 bg-teal-950/50 hover:bg-teal-900/60 text-teal-300 text-xs font-semibold transition-colors disabled:opacity-50"
              title="Dispatches a synthetic test alert to verify local and Blynk cloud notification pipelines"
            >
              {isTestingAlert ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-400" />
              ) : (
                <Send className="w-3.5 h-3.5 text-teal-400" />
              )}
              <span>Test Alert</span>
            </button>
          )}
        </div>
      </div>

      {/* List Content */}
      <div className="space-y-2.5 max-h-84 overflow-y-auto pr-1">
        {activeTab === "ALERTS" ? (
          filteredAlerts.length === 0 ? (
            <div className="py-8 text-center border border-dashed border-forest-850 rounded-lg bg-forest-950/30">
              <CheckCircle2 className="w-8 h-8 text-emerald-500/60 mx-auto mb-2" />
              <p className="text-xs font-semibold text-slate-300">No Threshold Alerts Logged</p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                All sensor parameters (temperature, humidity, MQ135 voltage, bin fill) are within normal boundaries.
              </p>
            </div>
          ) : (
            filteredAlerts.map((item) => (
              <div
                key={item.id}
                className={`p-3 rounded-lg border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors ${
                  item.severity === "CRITICAL"
                    ? "border-rose-500/30 bg-rose-950/20"
                    : item.severity === "WARNING"
                    ? "border-amber-500/30 bg-amber-950/20"
                    : "border-forest-800 bg-forest-950/40"
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <div
                    className={`p-1.5 rounded flex-shrink-0 mt-0.5 ${
                      item.severity === "CRITICAL"
                        ? "text-rose-400 bg-rose-500/20"
                        : "text-amber-400 bg-amber-500/20"
                    }`}
                  >
                    {item.severity === "CRITICAL" ? (
                      <AlertOctagon className="w-4 h-4" />
                    ) : (
                      <AlertTriangle className="w-4 h-4" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center flex-wrap gap-2">
                      <span className="font-bold text-white">{item.alert_type}</span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.2 rounded border ${
                          item.severity === "CRITICAL"
                            ? "bg-rose-950/80 text-rose-300 border-rose-500/40"
                            : "bg-amber-950/80 text-amber-300 border-amber-500/40"
                        }`}
                      >
                        {item.severity}
                      </span>

                      {item.metric_value !== null && item.threshold_value !== null && (
                        <span className="text-[11px] font-mono text-slate-400 bg-forest-950 px-1.5 py-0.5 rounded border border-forest-800">
                          Obs: {item.metric_value.toFixed(2)} &ge; Thr: {item.threshold_value.toFixed(2)}
                        </span>
                      )}

                      {item.blynk_delivered ? (
                        <span className="flex items-center gap-1 text-[10px] font-semibold text-teal-300 bg-teal-950/60 border border-teal-500/40 px-1.5 py-0.2 rounded">
                          <Cloud className="w-2.5 h-2.5 text-teal-400" />
                          Blynk Dispatched
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[10px] text-slate-400 bg-forest-950 border border-forest-850 px-1.5 py-0.2 rounded">
                          <CloudOff className="w-2.5 h-2.5 text-slate-500" />
                          Local Audit
                        </span>
                      )}

                      {item.is_mock && (
                        <span className="text-[9px] uppercase px-1 rounded bg-amber-900/50 text-amber-300 border border-amber-600/30">
                          Demo
                        </span>
                      )}
                    </div>
                    <p className="text-slate-300 mt-1">{item.message}</p>
                  </div>
                </div>

                <div className="text-right flex sm:flex-col items-center sm:items-end justify-between flex-shrink-0 font-mono text-slate-400 text-[11px]">
                  <span>{new Date(item.timestamp).toLocaleDateString()}</span>
                  <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            ))
          )
        ) : filteredAnomalies.length === 0 ? (
          <div className="py-8 text-center border border-dashed border-forest-850 rounded-lg bg-forest-950/30">
            <CheckCircle2 className="w-8 h-8 text-emerald-500/60 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-300">No Anomalies Logged in Lookback Window</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Environmental observations comply with Isolation Forest baseline distributions.
            </p>
          </div>
        ) : (
          filteredAnomalies.map((item) => (
            <div
              key={item.id}
              className={`p-3 rounded-lg border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors ${
                item.severity === "CRITICAL"
                  ? "border-rose-500/30 bg-rose-950/20"
                  : item.severity === "WARNING"
                  ? "border-amber-500/30 bg-amber-950/20"
                  : "border-forest-800 bg-forest-950/40"
              }`}
            >
              <div className="flex items-start gap-2.5">
                <div
                  className={`p-1.5 rounded flex-shrink-0 mt-0.5 ${
                    item.severity === "CRITICAL"
                      ? "text-rose-400 bg-rose-500/20"
                      : "text-amber-400 bg-amber-500/20"
                  }`}
                >
                  {item.severity === "CRITICAL" ? (
                    <AlertOctagon className="w-4 h-4" />
                  ) : (
                    <AlertTriangle className="w-4 h-4" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white">Event #{item.id}</span>
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.2 rounded border ${
                        item.severity === "CRITICAL"
                          ? "bg-rose-950/80 text-rose-300 border-rose-500/40"
                          : "bg-amber-950/80 text-amber-300 border-amber-500/40"
                      }`}
                    >
                      {item.severity}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400">
                      Score: {item.anomaly_score.toFixed(3)}
                    </span>
                    {item.is_demo && (
                      <span className="text-[9px] uppercase px-1 rounded bg-amber-900/50 text-amber-300">
                        Demo
                      </span>
                    )}
                  </div>
                  <p className="text-slate-300 mt-1">{item.explanation}</p>
                  <p className="text-[11px] text-teal-400 font-medium mt-0.5">
                    Action: {item.suggested_action}
                  </p>
                </div>
              </div>

              <div className="text-right flex sm:flex-col items-center sm:items-end justify-between flex-shrink-0 font-mono text-slate-400 text-[11px]">
                <span>{new Date(item.timestamp).toLocaleDateString()}</span>
                <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
