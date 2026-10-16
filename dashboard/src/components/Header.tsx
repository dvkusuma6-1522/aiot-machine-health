"use client";

import React from "react";
import {
  Activity,
  Cpu,
  FlaskConical,
  Radio,
  RefreshCw,
  Server,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Cloud,
  CloudOff,
} from "lucide-react";
import { formatRelativeTime } from "../lib/utils";
import { BlynkStatusResponse } from "../types/environment";

interface HeaderProps {
  deviceId: string;
  onDeviceChange: (id: string) => void;
  backendOnline: boolean | null;
  blynkStatus?: BlynkStatusResponse | null;
  lastSyncTime: string | null;
  isDemoMode: boolean;
  onToggleDemoMode: () => void;
  onOpenModelModal: () => void;
  onOpenDemoSelector: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  deviceId,
  onDeviceChange,
  backendOnline,
  blynkStatus,
  lastSyncTime,
  isDemoMode,
  onToggleDemoMode,
  onOpenModelModal,
  onOpenDemoSelector,
  onRefresh,
  isRefreshing,
}) => {
  return (
    <header className="border-b border-forest-800 bg-forest-950/90 backdrop-blur sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          {/* Title & Branding */}
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-400 shadow-inner">
              <Activity className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white">
                  Environmental Intelligence System
                </h1>
                <span className="text-[11px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-forest-800 border border-teal-500/30 text-teal-300">
                  AIoT Edge
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Multi-Sensor Edge Ingestion &bull; Random Forest Forecasting &bull; Isolation Forest Anomalies
              </p>
            </div>
          </div>

          {/* Action & Status Controls */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {/* Device ID Input / Selector */}
            <div className="flex items-center bg-forest-900 border border-forest-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300">
              <Radio className="w-3.5 h-3.5 text-teal-400 mr-2" />
              <span className="text-slate-400 mr-1.5">Node:</span>
              <input
                type="text"
                value={deviceId}
                onChange={(e) => onDeviceChange(e.target.value.trim())}
                placeholder="device_id"
                className="bg-transparent text-white font-mono font-medium focus:outline-none w-28 sm:w-32"
              />
            </div>

            {/* Quick Demo Node Toggle Button */}
            <button
              onClick={() => onDeviceChange(deviceId === "env_node_demo" ? "env_node_001" : "env_node_demo")}
              className="text-xs px-2.5 py-1.5 rounded-lg border border-forest-800 bg-forest-900 hover:bg-forest-850 text-slate-300 transition-colors"
              title="Toggle between physical hardware node and demo node"
            >
              {deviceId === "env_node_demo" ? "Use Hardware Node" : "Use Demo Node"}
            </button>

            {/* Backend Connection Indicator */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium ${
                backendOnline === true
                  ? "border-emerald-500/30 bg-emerald-950/30 text-emerald-300"
                  : backendOnline === false
                  ? "border-rose-500/30 bg-rose-950/30 text-rose-300"
                  : "border-slate-700 bg-slate-900 text-slate-400"
              }`}
            >
              <Server className="w-3.5 h-3.5" />
              <span>{backendOnline === true ? "API Online" : backendOnline === false ? "API Offline" : "Connecting..."}</span>
            </div>

            {/* Blynk IoT Cloud Connection Indicator */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium ${
                blynkStatus?.blynk_configured && blynkStatus?.blynk_enabled
                  ? "border-teal-500/30 bg-teal-950/30 text-teal-300"
                  : blynkStatus?.blynk_configured && !blynkStatus?.blynk_enabled
                  ? "border-amber-500/30 bg-amber-950/30 text-amber-300"
                  : "border-slate-800 bg-forest-900/60 text-slate-400"
              }`}
              title={
                blynkStatus?.blynk_configured
                  ? `Blynk Cloud: ${blynkStatus.server_url}`
                  : "Blynk Token Not Configured (Operating in Local Telemetry Mode)"
              }
            >
              {blynkStatus?.blynk_configured && blynkStatus?.blynk_enabled ? (
                <Cloud className="w-3.5 h-3.5 text-teal-400" />
              ) : (
                <CloudOff className="w-3.5 h-3.5 text-slate-500" />
              )}
              <span>
                {blynkStatus?.blynk_configured
                  ? blynkStatus?.blynk_enabled
                    ? "Blynk: Ready"
                    : "Blynk: Paused"
                  : "Blynk: Local Mode"}
              </span>
            </div>

            {/* Demonstration Mode Switch */}
            <button
              onClick={onToggleDemoMode}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-all ${
                isDemoMode
                  ? "bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.2)]"
                  : "bg-forest-900 border-forest-800 hover:border-forest-700 text-slate-400"
              }`}
            >
              <FlaskConical className={`w-3.5 h-3.5 ${isDemoMode ? "text-amber-400 animate-spin" : ""}`} />
              <span>Demo Mode: {isDemoMode ? "ON" : "OFF"}</span>
            </button>

            {/* Scenario Lab Trigger */}
            <button
              onClick={onOpenDemoSelector}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-teal-500/30 bg-teal-950/40 hover:bg-teal-900/50 text-teal-300 text-xs font-semibold transition-colors shadow-sm"
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>Scenarios</span>
            </button>

            {/* Model State Modal Trigger */}
            <button
              onClick={onOpenModelModal}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-forest-800 bg-forest-900 hover:bg-forest-850 text-slate-300 text-xs font-semibold transition-colors"
            >
              <Cpu className="w-3.5 h-3.5 text-teal-400" />
              <span>AI Lifecycle</span>
            </button>

            {/* Manual Refresh Button */}
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="p-2 rounded-lg border border-forest-800 bg-forest-900 hover:bg-forest-850 text-slate-300 hover:text-white disabled:opacity-50 transition-colors"
              title="Refresh telemetry"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-teal-400" : ""}`} />
            </button>
          </div>
        </div>

        {/* Sub-bar: Last synchronization status */}
        <div className="mt-2.5 pt-2 border-t border-forest-850 flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-teal-400 animate-ping" />
            <span>Active Polling Interval: 5s</span>
            <span>&bull;</span>
            <span>Last Telemetry Sync: <strong className="text-slate-300">{formatRelativeTime(lastSyncTime)}</strong></span>
          </div>
          <div className="hidden sm:flex items-center gap-3">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              <span>SQLite `(device_id, timestamp)`</span>
            </span>
            <span>&bull;</span>
            <span className="text-teal-400 font-mono text-[10px] bg-forest-900 border border-teal-500/30 px-1.5 py-0.5 rounded">
              Blynk V0–V7
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
