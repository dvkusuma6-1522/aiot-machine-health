"use client";

import React, { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  AreaChart,
  Area,
} from "recharts";
import { EnvironmentRecord } from "../types/environment";
import { formatTime } from "../lib/utils";
import { Clock, LineChart as ChartIcon, AlertCircle, RefreshCw } from "lucide-react";

interface HistoryChartsProps {
  records: EnvironmentRecord[];
  hours: number;
  onHoursChange: (hours: number) => void;
  loading: boolean;
  onRefresh: () => void;
}

export const HistoryCharts: React.FC<HistoryChartsProps> = ({
  records,
  hours,
  onHoursChange,
  loading,
  onRefresh,
}) => {
  const [activeTab, setActiveTab] = useState<"climate" | "air" | "waste">("air");

  // Transform records chronologically for Recharts
  const chartData = records.map((r) => ({
    time: formatTime(r.timestamp),
    rawTime: r.timestamp,
    temperature_c: r.temperature_c,
    humidity_percent: r.humidity_percent,
    mq135_voltage: r.mq135_voltage,
    mq135_raw: r.mq135_raw,
    ir_count: r.ir_count,
    bin_fill_percent: r.bin_fill_percent,
  }));

  const isEmpty = chartData.length === 0;

  return (
    <div className="rounded-xl border border-forest-800 bg-forest-900/60 p-5 space-y-4 shadow-sm">
      {/* Chart Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-forest-850 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
            <ChartIcon className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Historical Telemetry Trends
            </h3>
            <p className="text-[11px] text-slate-400">
              Composite indexed lookback series ({chartData.length} samples)
            </p>
          </div>
        </div>

        {/* Tab Selector & Time Range Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Category Tabs */}
          <div className="flex items-center bg-forest-950 rounded-lg p-1 border border-forest-800 text-xs">
            <button
              onClick={() => setActiveTab("air")}
              className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                activeTab === "air"
                  ? "bg-teal-500/20 text-teal-300 font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Air Quality
            </button>
            <button
              onClick={() => setActiveTab("climate")}
              className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                activeTab === "climate"
                  ? "bg-teal-500/20 text-teal-300 font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Climate
            </button>
            <button
              onClick={() => setActiveTab("waste")}
              className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                activeTab === "waste"
                  ? "bg-teal-500/20 text-teal-300 font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Activity &amp; Waste
            </button>
          </div>

          {/* Lookback Hour Filter */}
          <div className="flex items-center bg-forest-950 rounded-lg p-1 border border-forest-800 text-xs">
            {[1, 6, 24, 72].map((h) => (
              <button
                key={h}
                onClick={() => onHoursChange(h)}
                className={`px-2 py-1 rounded-md font-mono text-[11px] transition-colors ${
                  hours === h
                    ? "bg-forest-800 text-teal-300 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {h}h
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div className="w-full h-72 sm:h-80 relative">
        {loading && (
          <div className="absolute inset-0 bg-forest-950/60 backdrop-blur-xs flex items-center justify-center z-10 rounded-lg">
            <div className="flex items-center gap-2 text-teal-400 text-xs font-medium">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Querying historical telemetry window...</span>
            </div>
          </div>
        )}

        {isEmpty && !loading ? (
          <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 border border-dashed border-forest-800 rounded-lg bg-forest-950/30">
            <AlertCircle className="w-8 h-8 text-slate-500 mb-2" />
            <p className="text-sm font-semibold text-slate-300">No Historical Records Found</p>
            <p className="text-xs text-slate-500 mt-1 max-w-sm text-center">
              No telemetry stored for this device in the last {hours} hour(s). Transmit edge readings or select a Demonstration Scenario to populate data.
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {activeTab === "air" ? (
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="mqGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#14b8a6" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#0d382c" vertical={false} />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" domain={[0, 4.0]} tick={{ fontSize: 11 }} unit="V" />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                <ReferenceLine y={1.6} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "Poor Threshold (1.6V)", fill: "#f59e0b", fontSize: 10 }} />
                <ReferenceLine y={2.2} stroke="#f43f5e" strokeDasharray="4 4" label={{ value: "Hazard Threshold (2.2V)", fill: "#f43f5e", fontSize: 10 }} />
                <Area
                  type="monotone"
                  dataKey="mq135_voltage"
                  name="MQ135 Gas Voltage (V)"
                  stroke="#14b8a6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#mqGradient)"
                />
              </AreaChart>
            ) : activeTab === "climate" ? (
              <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#0d382c" vertical={false} />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="temp" stroke="#f97316" domain={["auto", "auto"]} tick={{ fontSize: 11 }} unit="°C" />
                <YAxis yAxisId="hum" orientation="right" stroke="#06b6d4" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                <Line
                  yAxisId="temp"
                  type="monotone"
                  dataKey="temperature_c"
                  name="Temperature (°C)"
                  stroke="#f97316"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="hum"
                  type="monotone"
                  dataKey="humidity_percent"
                  name="Humidity (% RH)"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            ) : (
              <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#0d382c" vertical={false} />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="fill" stroke="#10b981" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
                <YAxis yAxisId="ir" orientation="right" stroke="#a855f7" domain={["auto", "auto"]} tick={{ fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                <Line
                  yAxisId="fill"
                  type="monotone"
                  dataKey="bin_fill_percent"
                  name="Waste-Bin Fill (%)"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="ir"
                  type="stepAfter"
                  dataKey="ir_count"
                  name="IR Footfall Count"
                  stroke="#a855f7"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

// Custom Tooltip component for dark mode styling
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-forest-950 border border-forest-800 p-2.5 rounded-lg shadow-xl text-xs space-y-1">
        <p className="font-mono text-slate-400 border-b border-forest-850 pb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={`item-${index}`} className="flex items-center justify-between gap-4 font-mono">
            <span style={{ color: entry.color }}>{entry.name}:</span>
            <span className="font-bold text-white">
              {entry.value !== null && entry.value !== undefined ? Number(entry.value).toFixed(2) : "--"}
            </span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};
