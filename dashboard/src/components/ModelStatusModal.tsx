"use client";

import React, { useState } from "react";
import { X, Cpu, RefreshCw, CheckCircle2, AlertTriangle, Database, FolderCheck } from "lucide-react";
import { ModelSystemStatusResponse } from "../types/environment";
import { trainModels } from "../lib/api";

interface ModelStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
  status: ModelSystemStatusResponse | null;
  deviceId: string;
  onRetrainSuccess: () => void;
}

export const ModelStatusModal: React.FC<ModelStatusModalProps> = ({
  isOpen,
  onClose,
  status,
  deviceId,
  onRetrainSuccess,
}) => {
  const [allowMockData, setAllowMockData] = useState<boolean>(true);
  const [minSamples, setMinSamples] = useState<number>(100);
  const [isTraining, setIsTraining] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isError, setIsError] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleTrain = async () => {
    setIsTraining(true);
    setFeedback(null);
    setIsError(false);
    try {
      const res: any = await trainModels({
        device_id: deviceId,
        allow_mock_data: allowMockData,
        min_samples: minSamples,
        test_size: 0.25,
      });

      if (res.status === "WAITING_FOR_DATA") {
        setIsError(true);
        setFeedback(res.message);
      } else {
        setFeedback(res.message || "Models trained and persisted successfully!");
        onRetrainSuccess();
      }
    } catch (err: any) {
      setIsError(true);
      setFeedback(err.message || "Failed to trigger training.");
    } finally {
      setIsTraining(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="rounded-xl border border-teal-500/30 bg-forest-950 p-6 max-w-lg w-full shadow-2xl space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-forest-850 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-teal-500/10 text-teal-300 border border-teal-500/30">
              <Cpu className="w-5 h-5 text-teal-400" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                AI Model Operational Lifecycle
              </h3>
              <p className="text-xs text-slate-400">
                Persistent Scikit-Learn estimators &bull; models/environment/
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

        {/* Status Grid */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          {/* RF Forecaster */}
          <div className="p-3 rounded-lg bg-forest-900/60 border border-forest-800 space-y-1">
            <span className="text-slate-400 block font-medium">Random Forest Forecaster</span>
            <span className="text-sm font-bold text-teal-300 block font-mono">
              {status?.forecaster_status || "Initializing"}
            </span>
            <div className="text-[11px] text-slate-400">
              Version: <strong className="text-slate-200">{status?.forecaster_version || "rf-v1.0"}</strong>
            </div>
            <div className="text-[10px] text-slate-500 pt-1">
              MAE: {status?.forecaster_mae !== null && status?.forecaster_mae !== undefined ? `${status.forecaster_mae.toFixed(4)}V` : "N/A"}
            </div>
          </div>

          {/* Isolation Forest */}
          <div className="p-3 rounded-lg bg-forest-900/60 border border-forest-800 space-y-1">
            <span className="text-slate-400 block font-medium">Isolation Forest Outliers</span>
            <span className="text-sm font-bold text-teal-300 block font-mono">
              {status?.anomaly_detector_status || "Initializing"}
            </span>
            <div className="text-[11px] text-slate-400">
              Version: <strong className="text-slate-200">{status?.anomaly_detector_version || "iso-v1.0"}</strong>
            </div>
            <div className="text-[10px] text-slate-500 pt-1">
              Contamination: &nu; = 0.05
            </div>
          </div>
        </div>

        {/* Database & Storage Status */}
        <div className="p-3 rounded-lg bg-forest-900/40 border border-forest-800 text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-400">
              <Database className="w-3.5 h-3.5 text-teal-400" />
              <span>Database Telemetry Records:</span>
            </span>
            <span className="font-mono text-white font-bold">
              {status?.database_reading_count ?? 0} samples
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-400">
              <FolderCheck className="w-3.5 h-3.5 text-teal-400" />
              <span>Models Serialized to Disk:</span>
            </span>
            <span className={`font-semibold ${status?.models_persisted ? "text-emerald-400" : "text-amber-400"}`}>
              {status?.models_persisted ? "Persisted (.joblib)" : "Pending Training"}
            </span>
          </div>
        </div>

        {/* Retraining Controls */}
        <div className="pt-2 border-t border-forest-850 space-y-3">
          <h4 className="text-xs font-semibold text-white">Trigger Model Retraining</h4>

          <div className="flex items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              id="allowMockCheckbox"
              checked={allowMockData}
              onChange={(e) => setAllowMockData(e.target.checked)}
              className="accent-teal-500 rounded cursor-pointer"
            />
            <label htmlFor="allowMockCheckbox" className="cursor-pointer">
              Allow Demonstration/Mock Data if real database is sparse (&lt; 100)
            </label>
          </div>

          {feedback && (
            <div
              className={`p-2.5 rounded-lg text-xs flex items-center gap-2 ${
                isError
                  ? "bg-rose-950/50 border border-rose-500/30 text-rose-300"
                  : "bg-emerald-950/50 border border-emerald-500/30 text-emerald-300"
              }`}
            >
              {isError ? <AlertTriangle className="w-4 h-4 flex-shrink-0" /> : <CheckCircle2 className="w-4 h-4 flex-shrink-0" />}
              <span>{feedback}</span>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition-colors"
            >
              Dismiss
            </button>
            <button
              onClick={handleTrain}
              disabled={isTraining}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-forest-950 font-bold text-xs shadow-md transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isTraining ? "animate-spin" : ""}`} />
              <span>{isTraining ? "Fitting Models..." : "Train Pipelines"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
