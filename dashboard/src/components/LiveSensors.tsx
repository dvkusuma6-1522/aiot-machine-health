"use client";

import React from "react";
import {
  Thermometer,
  Droplets,
  Wind,
  Footprints,
  Trash2,
  Cpu,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Zap,
} from "lucide-react";
import { EnvironmentRecord } from "../types/environment";
import { formatNumber, getAirQualityLevel } from "../lib/utils";

interface LiveSensorsProps {
  telemetry: EnvironmentRecord | null;
  loading: boolean;
}

export const LiveSensors: React.FC<LiveSensorsProps> = ({ telemetry, loading }) => {
  const airQuality = getAirQualityLevel(telemetry?.mq135_voltage);
  const fillPct = telemetry?.bin_fill_percent;

  const probeStatus = telemetry?.sensor_status || {};

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <span>Live Multi-Sensor Readings</span>
            {telemetry?.is_mock && (
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-500/30">
                Mock Source
              </span>
            )}
          </h2>
          <p className="text-xs text-slate-400">
            Real-time environmental observations ingested from edge firmware
          </p>
        </div>
        {telemetry && (
          <div className="text-[11px] font-mono text-slate-400">
            Observed: <span className="text-teal-300">{new Date(telemetry.timestamp).toLocaleTimeString()}</span>
          </div>
        )}
      </div>

      {/* 6 Sensor Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
        {/* 1. Ambient Temperature */}
        <div className="rounded-xl border border-forest-800 bg-forest-900/60 p-4 relative overflow-hidden flex flex-col justify-between hover:border-teal-500/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Temperature</span>
            <div className="p-1.5 rounded-lg bg-orange-500/10 text-orange-400 border border-orange-500/20">
              <Thermometer className="w-4 h-4" />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-extrabold text-white tracking-tight font-mono">
              {formatNumber(telemetry?.temperature_c, 1)}
              <span className="text-sm font-normal text-slate-400 ml-1">&deg;C</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {telemetry?.temperature_c !== null && telemetry?.temperature_c !== undefined ? (
                telemetry.temperature_c >= 18 && telemetry.temperature_c <= 28 ? (
                  <span className="text-emerald-400">Comfort Zone</span>
                ) : (
                  <span className="text-amber-400">Outside Comfort Range</span>
                )
              ) : (
                <span className="text-slate-500 italic">Sensor Unavailable</span>
              )}
            </div>
          </div>
          <div className="pt-2 border-t border-forest-850 flex items-center justify-between text-[10px] text-slate-400">
            <span>Probe: DHT22</span>
            <StatusPill status={probeStatus.dht22} />
          </div>
        </div>

        {/* 2. Relative Humidity */}
        <div className="rounded-xl border border-forest-800 bg-forest-900/60 p-4 relative overflow-hidden flex flex-col justify-between hover:border-teal-500/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Humidity</span>
            <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Droplets className="w-4 h-4" />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-extrabold text-white tracking-tight font-mono">
              {formatNumber(telemetry?.humidity_percent, 1)}
              <span className="text-sm font-normal text-slate-400 ml-1">% RH</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {telemetry?.humidity_percent !== null && telemetry?.humidity_percent !== undefined ? (
                telemetry.humidity_percent >= 30 && telemetry.humidity_percent <= 60 ? (
                  <span className="text-emerald-400">Optimal Range</span>
                ) : (
                  <span className="text-amber-400">Suboptimal Humidity</span>
                )
              ) : (
                <span className="text-slate-500 italic">Sensor Unavailable</span>
              )}
            </div>
          </div>
          <div className="pt-2 border-t border-forest-850 flex items-center justify-between text-[10px] text-slate-400">
            <span>Probe: DHT22</span>
            <StatusPill status={probeStatus.dht22} />
          </div>
        </div>

        {/* 3. MQ135 Air Quality Voltage */}
        <div className={`rounded-xl border ${airQuality.border} ${airQuality.bg} p-4 relative overflow-hidden flex flex-col justify-between transition-colors`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Air Quality (MQ135)</span>
            <div className={`p-1.5 rounded-lg bg-teal-500/10 ${airQuality.color} border border-teal-500/20`}>
              <Wind className="w-4 h-4" />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-extrabold text-white tracking-tight font-mono">
              {formatNumber(telemetry?.mq135_voltage, 2)}
              <span className="text-sm font-normal text-slate-400 ml-1">V</span>
            </div>
            <div className="text-[11px] font-semibold mt-1">
              <span className={airQuality.color}>{airQuality.label}</span>
              {telemetry?.mq135_voltage !== null && telemetry?.mq135_voltage !== undefined && (
                <span className="text-slate-400 font-normal ml-1">
                  ({telemetry.mq135_voltage < 1.0 ? "<1.0V" : telemetry.mq135_voltage < 1.6 ? "1.0-1.6V" : ">1.6V"})
                </span>
              )}
            </div>
          </div>
          <div className="pt-2 border-t border-forest-850 flex items-center justify-between text-[10px] text-slate-400">
            <span>Raw ADC: {formatNumber(telemetry?.mq135_raw, 0)}</span>
            <StatusPill status={probeStatus.mq135} />
          </div>
        </div>

        {/* 4. MQ135 Raw ADC (12-bit) */}
        <div className="rounded-xl border border-forest-800 bg-forest-900/60 p-4 relative overflow-hidden flex flex-col justify-between hover:border-teal-500/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">ADC1 Value</span>
            <div className="p-1.5 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-extrabold text-white tracking-tight font-mono">
              {formatNumber(telemetry?.mq135_raw, 0)}
              <span className="text-sm font-normal text-slate-400 ml-1">/ 4095</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {telemetry?.mq135_raw !== null && telemetry?.mq135_raw !== undefined ? (
                <span>GPIO 34 ADC1 (12-bit)</span>
              ) : (
                <span className="text-slate-500 italic">No ADC Input</span>
              )}
            </div>
          </div>
          <div className="pt-2 border-t border-forest-850 flex items-center justify-between text-[10px] text-slate-400">
            <span>Atten: 11dB (0-3.3V)</span>
            <StatusPill status={probeStatus.mq135} />
          </div>
        </div>

        {/* 5. IR Activity Count */}
        <div className="rounded-xl border border-forest-800 bg-forest-900/60 p-4 relative overflow-hidden flex flex-col justify-between hover:border-teal-500/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">IR Traffic Count</span>
            <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Footprints className="w-4 h-4" />
            </div>
          </div>
          <div className="my-2">
            <div className="text-2xl font-extrabold text-white tracking-tight font-mono">
              {telemetry?.ir_count !== null && telemetry?.ir_count !== undefined
                ? telemetry.ir_count
                : "--"}
              <span className="text-sm font-normal text-slate-400 ml-1">events</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {telemetry?.ir_count !== null && telemetry?.ir_count !== undefined ? (
                <span>Footfall / Occupancy</span>
              ) : (
                <span className="text-slate-500 italic">Sensor Unavailable</span>
              )}
            </div>
          </div>
          <div className="pt-2 border-t border-forest-850 flex items-center justify-between text-[10px] text-slate-400">
            <span>GPIO 27 Edge Count</span>
            <StatusPill status={probeStatus.ir} />
          </div>
        </div>

        {/* 6. Ultrasonic Waste-Bin Fill */}
        <div className="rounded-xl border border-forest-800 bg-forest-900/60 p-4 relative overflow-hidden flex flex-col justify-between hover:border-teal-500/40 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Waste-Bin Fill</span>
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Trash2 className="w-4 h-4" />
            </div>
          </div>
          <div className="my-2">
            <div className="flex items-baseline justify-between">
              <div className="text-2xl font-extrabold text-white tracking-tight font-mono">
                {formatNumber(fillPct, 1)}
                <span className="text-sm font-normal text-slate-400 ml-1">%</span>
              </div>
              <div className="text-[11px] font-mono text-slate-400">
                {formatNumber(telemetry?.ultrasonic_distance_cm, 1)} cm
              </div>
            </div>
            {/* Visual Fill Gauge Bar */}
            <div className="w-full bg-forest-950 rounded-full h-2 mt-2 overflow-hidden border border-forest-800">
              <div
                className={`h-full transition-all duration-500 rounded-full ${
                  fillPct !== null && fillPct !== undefined
                    ? fillPct > 80
                      ? "bg-rose-500"
                      : fillPct > 60
                      ? "bg-amber-500"
                      : "bg-teal-400"
                    : "bg-slate-700 w-0"
                }`}
                style={{ width: `${Math.min(100, Math.max(0, fillPct ?? 0))}%` }}
              />
            </div>
          </div>
          <div className="pt-2 border-t border-forest-850 flex items-center justify-between text-[10px] text-slate-400">
            <span>Probe: HC-SR04</span>
            <StatusPill status={probeStatus.ultrasonic} />
          </div>
        </div>
      </div>
    </div>
  );
};

const StatusPill: React.FC<{ status?: string }> = ({ status }) => {
  if (status === "OK") {
    return (
      <span className="flex items-center gap-1 text-emerald-400 font-semibold">
        <CheckCircle2 className="w-3 h-3" /> OK
      </span>
    );
  }
  if (status === "FAIL") {
    return (
      <span className="flex items-center gap-1 text-rose-400 font-semibold">
        <XCircle className="w-3 h-3" /> FAIL
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-slate-500">
      <HelpCircle className="w-3 h-3" /> N/A
    </span>
  );
};
