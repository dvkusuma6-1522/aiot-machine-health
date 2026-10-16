"use client";

import React from "react";
import { AlertTriangle, FlaskConical, Sliders, X } from "lucide-react";

interface DemoBannerProps {
  isDemoMode: boolean;
  isMockData: boolean;
  onOpenScenarios: () => void;
  onExitDemo: () => void;
}

export const DemoBanner: React.FC<DemoBannerProps> = ({
  isDemoMode,
  isMockData,
  onOpenScenarios,
  onExitDemo,
}) => {
  if (!isDemoMode && !isMockData) return null;

  return (
    <div className="bg-gradient-to-r from-amber-950/80 via-forest-900/90 to-amber-950/80 border-b border-amber-500/40 text-amber-200 px-4 py-2.5 text-xs shadow-md">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2.5">
        <div className="flex items-center gap-2 text-center sm:text-left">
          <div className="p-1 rounded bg-amber-500/20 text-amber-400">
            <AlertTriangle className="w-4 h-4 animate-bounce" />
          </div>
          <div>
            <strong className="font-semibold text-amber-300">DEMONSTRATION BENCH MODE ACTIVE:</strong>{" "}
            <span>
              Telemetry and model outputs are generated from calibrated synthetic scenarios (provenance:{" "}
              <code className="bg-amber-900/60 px-1 py-0.5 rounded text-amber-100 font-mono">is_mock=True</code>). Real physical sensor inputs are bypassed.
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={onOpenScenarios}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-200 text-xs font-semibold transition-colors"
          >
            <Sliders className="w-3 h-3 text-amber-400" />
            <span>Switch Scenario</span>
          </button>
          <button
            onClick={onExitDemo}
            className="flex items-center gap-1 px-2 py-1 rounded bg-forest-900/80 hover:bg-forest-850 border border-slate-700 text-slate-300 text-xs transition-colors"
            title="Exit Demo Mode"
          >
            <X className="w-3.5 h-3.5" />
            <span>Dismiss</span>
          </button>
        </div>
      </div>
    </div>
  );
};
