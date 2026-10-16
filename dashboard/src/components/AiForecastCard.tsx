"use client";

import React from "react";
import { Sparkles, TrendingUp, TrendingDown, Minus, Clock, ShieldAlert, Cpu, BarChart2 } from "lucide-react";
import { PredictionResponse } from "../types/environment";
import { formatNumber, formatTime } from "../lib/utils";

interface AiForecastCardProps {
  prediction: PredictionResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

export const AiForecastCard: React.FC<AiForecastCardProps> = ({ prediction, loading, onRefresh }) => {
  const isWaiting = prediction?.model_status === "WAITING_FOR_DATA";
  const isDemo = prediction?.is_demonstration || false;
  const currentVal = prediction?.current_mq135_voltage;
  const predVal = prediction?.predicted_value;

  // Trend direction
  const delta = currentVal !== null && currentVal !== undefined && predVal !== null && predVal !== undefined
    ? predVal - currentVal
    : null;

  return (
    <div className="rounded-xl border border-teal-500/30 bg-gradient-to-b from-forest-900/80 to-forest-950/90 p-5 space-y-4 shadow-sm relative overflow-hidden">
      {/* Decorative ambient gradient */}
      <div className="absolute top-0 right-0 w-48 h-48 bg-teal-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between border-b border-forest-850 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-teal-500/10 text-teal-300 border border-teal-500/30">
            <Sparkles className="w-4 h-4 text-teal-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white tracking-tight">
                60-Minute Ahead MQ135 Forecast
              </h3>
              {isDemo && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-500/40">
                  Demonstration Forecast
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400">
              Scikit-Learn Random Forest Regressor (100 Decision Trees)
            </p>
          </div>
        </div>

        {/* Model Status Badge */}
        <div>
          {isWaiting ? (
            <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-amber-950/60 text-amber-300 border border-amber-500/30">
              Waiting for Data
            </span>
          ) : prediction?.model_status === "MODEL_EVALUATED" ? (
            <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
              Model Evaluated
            </span>
          ) : (
            <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-teal-950/60 text-teal-300 border border-teal-500/30">
              {prediction?.model_status || "Initializing"}
            </span>
          )}
        </div>
      </div>

      {/* Core Forecast Display */}
      {isWaiting ? (
        <div className="py-6 px-4 rounded-lg bg-forest-950/50 border border-forest-800 text-center space-y-2">
          <ShieldAlert className="w-8 h-8 text-amber-400 mx-auto" />
          <h4 className="text-sm font-semibold text-white">Insufficient Historical Telemetry</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            {prediction?.message || "Collecting time-series readings. At least 100 historical readings (~2 hours) are required to avoid artificial accuracy."}
          </p>
          <div className="pt-2 text-[11px] text-teal-400 font-mono">
            Toggle &ldquo;Demo Mode&rdquo; in the header to view an illustrative calibrated forecast.
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Current vs Predicted Comparison */}
          <div className="rounded-lg bg-forest-950/80 border border-forest-800 p-4 space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>Current vs Target (+60m)</span>
              <span className="font-mono text-slate-500">
                Target: {prediction?.target_timestamp ? formatTime(prediction.target_timestamp) : "--:--"}
              </span>
            </div>

            <div className="flex items-baseline justify-between">
              <div>
                <span className="text-[11px] text-slate-400 block">Baseline (Now)</span>
                <span className="text-xl font-bold font-mono text-slate-300">
                  {formatNumber(currentVal, 2)}V
                </span>
              </div>

              <div className="flex items-center text-xs px-2 py-1 rounded bg-forest-900 border border-forest-800">
                {delta !== null ? (
                  delta > 0.05 ? (
                    <span className="flex items-center text-rose-400 gap-1 font-semibold">
                      <TrendingUp className="w-3.5 h-3.5" /> +{formatNumber(delta, 2)}V (Rising)
                    </span>
                  ) : delta < -0.05 ? (
                    <span className="flex items-center text-emerald-400 gap-1 font-semibold">
                      <TrendingDown className="w-3.5 h-3.5" /> {formatNumber(delta, 2)}V (Falling)
                    </span>
                  ) : (
                    <span className="flex items-center text-slate-300 gap-1">
                      <Minus className="w-3.5 h-3.5" /> Stable
                    </span>
                  )
                ) : (
                  <span className="text-slate-500">--</span>
                )}
              </div>

              <div className="text-right">
                <span className="text-[11px] text-teal-400 block font-semibold">Forecast (t+60m)</span>
                <span className="text-2xl font-extrabold font-mono text-teal-300">
                  {formatNumber(predVal, 2)}V
                </span>
              </div>
            </div>

            {/* Quantile Prediction Interval (10th to 90th percentile) */}
            <div className="pt-2 border-t border-forest-850">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-400">80% Ensemble Interval:</span>
                <span className="font-mono text-teal-300 font-semibold">
                  [{formatNumber(prediction?.confidence_lower, 2)}V &mdash; {formatNumber(prediction?.confidence_upper, 2)}V]
                </span>
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5">
                Calculated from empirical 10th and 90th quantiles across 100 decision trees.
              </p>
            </div>
          </div>

          {/* Real Metrics & Model Metadata */}
          <div className="rounded-lg bg-forest-950/80 border border-forest-800 p-4 space-y-3 flex flex-col justify-between">
            <div>
              <span className="text-xs font-semibold text-white block mb-1">
                Evaluation Metrics (Held-Out Test Set)
              </span>
              <p className="text-[11px] text-slate-400">
                Metrics calculated chronologically on unseen test split; never fabricated.
              </p>

              <div className="grid grid-cols-2 gap-2 mt-3">
                <div className="p-2 rounded bg-forest-900 border border-forest-850">
                  <span className="text-[10px] text-slate-400 block">MAE (Mean Abs Error)</span>
                  <span className="text-sm font-bold font-mono text-slate-200">
                    {prediction?.mae !== null && prediction?.mae !== undefined ? `${prediction.mae.toFixed(4)} V` : "Pending Data"}
                  </span>
                </div>
                <div className="p-2 rounded bg-forest-900 border border-forest-850">
                  <span className="text-[10px] text-slate-400 block">RMSE (Root Mean Sq)</span>
                  <span className="text-sm font-bold font-mono text-slate-200">
                    {prediction?.rmse !== null && prediction?.rmse !== undefined ? `${prediction.rmse.toFixed(4)} V` : "Pending Data"}
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-forest-850 flex items-center justify-between text-[10px] text-slate-400 font-mono">
              <span>Version: {prediction?.model_version || "rf-v1.0"}</span>
              <span>Horizon: 60 minutes</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
