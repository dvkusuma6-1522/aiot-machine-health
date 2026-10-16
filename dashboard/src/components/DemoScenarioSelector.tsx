"use client";

import React, { useState } from "react";
import { X, Play, Sliders, CheckCircle2, AlertTriangle, Layers, Activity } from "lucide-react";
import { injectDemoScenario } from "../lib/api";

interface DemoScenarioSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  deviceId: string;
  onScenarioInjected: () => void;
}

const SCENARIOS = [
  {
    id: "normal",
    title: "1. Nominal Climate Baseline",
    badge: "Normal",
    badgeColor: "text-emerald-400 bg-emerald-950/60 border-emerald-500/30",
    description: "Stable baseline indoor climate. Normal diurnal temperature (22-26°C), optimal humidity (45-55%), clean air quality (<1.2V), low traffic.",
  },
  {
    id: "increasing_mq135",
    title: "2. Progressive Gas Concentration Drift",
    badge: "Warning",
    badgeColor: "text-amber-400 bg-amber-950/60 border-amber-500/30",
    description: "Steadily rising air pollution trajectory simulating progressive accumulation of volatile gas emissions over time (from 1.0V to 3.2V).",
  },
  {
    id: "spike_mq135",
    title: "3. Episodic Gas Voltage Spike",
    badge: "Spike",
    badgeColor: "text-rose-400 bg-rose-950/60 border-rose-500/30",
    description: "Sharp transient Gaussian air quality spike in the middle of observation window. Tests sensitivity to localized hazardous gas events.",
  },
  {
    id: "multivariate_anomaly",
    title: "4. Multi-Sensor Divergence",
    badge: "Critical",
    badgeColor: "text-rose-400 bg-rose-950/60 border-rose-500/30",
    description: "Simultaneous thermal surge (+10.5°C), high humidity, elevated gas, and heavy traffic. Tests Isolation Forest multi-sensor attribution.",
  },
  {
    id: "longitudinal_forecasting",
    title: "5. Diurnal ML Training Series",
    badge: "ML Ready",
    badgeColor: "text-teal-400 bg-teal-950/60 border-teal-500/30",
    description: "Multi-hour smooth cyclical variations suitable for training the Random Forest 60-minute ahead regressor without synthetic artifacts.",
  },
];

export const DemoScenarioSelector: React.FC<DemoScenarioSelectorProps> = ({
  isOpen,
  onClose,
  deviceId,
  onScenarioInjected,
}) => {
  const [selectedScenario, setSelectedScenario] = useState<string>("normal");
  const [nSamples, setNSamples] = useState<number>(60);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isError, setIsError] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleInject = async () => {
    setSubmitting(true);
    setFeedback(null);
    setIsError(false);
    try {
      const res = await injectDemoScenario({
        scenario: selectedScenario as any,
        device_id: deviceId,
        n_samples: nSamples,
        sample_interval_sec: 60,
        clear_previous_demo: true,
      });
      setFeedback(res.message);
      onScenarioInjected();
    } catch (err: any) {
      setIsError(true);
      setFeedback(err.message || "Failed to inject scenario.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="rounded-xl border border-teal-500/30 bg-forest-950 p-6 max-w-xl w-full shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-forest-850 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-teal-500/10 text-teal-300 border border-teal-500/30">
              <Sliders className="w-5 h-5 text-teal-400" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Demonstration Scenario Laboratory
              </h3>
              <p className="text-xs text-slate-400">
                Inject calibrated synthetic multi-sensor sequences (provenance: is_mock=True)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-forest-900 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Target Device */}
        <div className="p-2.5 rounded-lg bg-forest-900/60 border border-forest-800 flex items-center justify-between text-xs">
          <span className="text-slate-400">Target Device Node:</span>
          <span className="font-mono text-teal-300 font-bold">{deviceId}</span>
        </div>

        {/* Scenario Selection Grid */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-slate-300 block">Select Scenario Pattern:</label>
          <div className="space-y-2">
            {SCENARIOS.map((sc) => (
              <div
                key={sc.id}
                onClick={() => setSelectedScenario(sc.id)}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  selectedScenario === sc.id
                    ? "border-teal-500 bg-teal-950/30 shadow-inner"
                    : "border-forest-850 bg-forest-900/40 hover:border-forest-750"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">{sc.title}</span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${sc.badgeColor}`}>
                    {sc.badge}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">{sc.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Sample Count Slider */}
        <div className="space-y-1.5 pt-1">
          <div className="flex justify-between text-xs">
            <span className="text-slate-300 font-medium">Sample Count:</span>
            <span className="font-mono text-teal-300 font-bold">{nSamples} readings ({Math.round(nSamples / 60 * 10) / 10} hours)</span>
          </div>
          <input
            type="range"
            min={20}
            max={180}
            step={10}
            value={nSamples}
            onChange={(e) => setNSamples(Number(e.target.value))}
            className="w-full accent-teal-400 bg-forest-900 h-2 rounded-lg cursor-pointer"
          />
          <span className="text-[10px] text-slate-500 block">
            Tip: Select &ge; 100 samples if planning to train the Random Forest model on this scenario.
          </span>
        </div>

        {/* Feedback message */}
        {feedback && (
          <div
            className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
              isError
                ? "bg-rose-950/50 border border-rose-500/30 text-rose-300"
                : "bg-emerald-950/50 border border-emerald-500/30 text-emerald-300"
            }`}
          >
            {isError ? <AlertTriangle className="w-4 h-4 flex-shrink-0" /> : <CheckCircle2 className="w-4 h-4 flex-shrink-0" />}
            <span>{feedback}</span>
          </div>
        )}

        {/* Actions */}
        <div className="pt-2 border-t border-forest-850 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition-colors"
          >
            Close
          </button>
          <button
            onClick={handleInject}
            disabled={submitting}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-500 hover:bg-teal-400 text-forest-950 font-bold text-xs shadow-md transition-colors disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${submitting ? "animate-spin" : ""}`} />
            <span>{submitting ? "Injecting..." : "Inject Scenario Telemetry"}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
