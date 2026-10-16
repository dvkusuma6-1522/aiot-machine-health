"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "../components/Header";
import { DemoBanner } from "../components/DemoBanner";
import { LiveSensors } from "../components/LiveSensors";
import { HistoryCharts } from "../components/HistoryCharts";
import { AiForecastCard } from "../components/AiForecastCard";
import { AnomalyDetectorCard } from "../components/AnomalyDetectorCard";
import { AlertHistoryList } from "../components/AlertHistoryList";
import { DemoScenarioSelector } from "../components/DemoScenarioSelector";
import { ModelStatusModal } from "../components/ModelStatusModal";

import {
  checkBackendHealth,
  getLatestTelemetry,
  getHistoricalTelemetry,
  getPrediction,
  getAnomalies,
  getModelStatus,
  getAlerts,
  getBlynkStatus,
  triggerTestAlert,
} from "../lib/api";

import {
  EnvironmentRecord,
  PredictionResponse,
  AnomalyItem,
  ModelSystemStatusResponse,
  AlertRecord,
  BlynkStatusResponse,
} from "../types/environment";

export default function DashboardPage() {
  const [deviceId, setDeviceId] = useState<string>("env_node_001");
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);

  // Data states
  const [telemetry, setTelemetry] = useState<EnvironmentRecord | null>(null);
  const [historyRecords, setHistoryRecords] = useState<EnvironmentRecord[]>([]);
  const [historyHours, setHistoryHours] = useState<number>(1.0);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [blynkStatus, setBlynkStatus] = useState<BlynkStatusResponse | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelSystemStatusResponse | null>(null);

  // Loading & Modal UI states
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isTestingAlert, setIsTestingAlert] = useState<boolean>(false);
  const [isDemoSelectorOpen, setIsDemoSelectorOpen] = useState<boolean>(false);
  const [isModelModalOpen, setIsModelModalOpen] = useState<boolean>(false);

  // Fetch all dashboard data
  const fetchData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // 1. Backend health check
      const health = await checkBackendHealth();
      setBackendOnline(health !== null);

      if (health) {
        // 2. Latest reading
        const latest = await getLatestTelemetry(deviceId);
        setTelemetry(latest);

        // 3. History window
        const hist = await getHistoricalTelemetry(deviceId, historyHours, 100);
        setHistoryRecords(hist.items || []);

        // 4. ML Prediction (Random Forest)
        const pred = await getPrediction(deviceId, isDemoMode);
        setPrediction(pred);

        // 5. Isolation Forest Anomalies
        const anom = await getAnomalies(deviceId, 24.0, 50);
        setAnomalies(anom.items || []);

        // 6. Threshold & Blynk Alerts
        const alertRes = await getAlerts(deviceId, 24.0, 50);
        setAlerts(alertRes.items || []);

        // 7. Blynk Integration Status
        const blynkRes = await getBlynkStatus();
        setBlynkStatus(blynkRes);

        // 8. Model Lifecycle Status
        const statusRes = await getModelStatus();
        setModelStatus(statusRes);

        setLastSyncTime(new Date().toISOString());
      }
    } catch (err) {
      console.error("Dashboard poll failed:", err);
      // Non-fatal: keep current state, mark backend status
      setBackendOnline(false);
    } finally {
      setIsRefreshing(false);
    }
  }, [deviceId, historyHours, isDemoMode]);

  // Periodic polling (every 5 seconds)
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Handle switching to demo node
  const handleDeviceChange = (newId: string) => {
    setDeviceId(newId);
    if (newId.includes("demo")) {
      setIsDemoMode(true);
    }
  };

  // Trigger test alert handler
  const handleTriggerTestAlert = async () => {
    setIsTestingAlert(true);
    try {
      await triggerTestAlert({
        device_id: deviceId,
        alert_type: "HIGH_MQ135",
        metric_value: 2.45,
        severity: "WARNING",
        message: "Demonstration alert: MQ135 sensor response reached 2.45V exceeding 2.0V threshold.",
      });
      await fetchData();
    } catch (err) {
      console.error("Trigger test alert failed:", err);
    } finally {
      setIsTestingAlert(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-forest-950 text-slate-100">
      {/* 1. Header */}
      <Header
        deviceId={deviceId}
        onDeviceChange={handleDeviceChange}
        backendOnline={backendOnline}
        blynkStatus={blynkStatus}
        lastSyncTime={lastSyncTime}
        isDemoMode={isDemoMode}
        onToggleDemoMode={() => setIsDemoMode((prev) => !prev)}
        onOpenModelModal={() => setIsModelModalOpen(true)}
        onOpenDemoSelector={() => setIsDemoSelectorOpen(true)}
        onRefresh={fetchData}
        isRefreshing={isRefreshing}
      />

      {/* 2. Demonstration Warning Banner */}
      <DemoBanner
        isDemoMode={isDemoMode}
        isMockData={telemetry?.is_mock || false}
        onOpenScenarios={() => setIsDemoSelectorOpen(true)}
        onExitDemo={() => setIsDemoMode(false)}
      />

      {/* 3. Main Dashboard Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Section A: Live Multi-Sensor Telemetry */}
        <section>
          <LiveSensors telemetry={telemetry} loading={isRefreshing} />
        </section>

        {/* Section B: Historical Charts & AI Analytics */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Historical Trends (7 cols on lg) */}
          <div className="lg:col-span-7">
            <HistoryCharts
              records={historyRecords}
              hours={historyHours}
              onHoursChange={(h) => setHistoryHours(h)}
              loading={isRefreshing}
              onRefresh={fetchData}
            />
          </div>

          {/* AI Cards Stack (5 cols on lg) */}
          <div className="lg:col-span-5 space-y-6">
            <AiForecastCard
              prediction={prediction}
              loading={isRefreshing}
              onRefresh={fetchData}
            />

            <AnomalyDetectorCard
              latestAnomaly={anomalies.length > 0 ? anomalies[0] : null}
              loading={isRefreshing}
            />
          </div>
        </section>

        {/* Section C: Alert & Anomaly Event History */}
        <section>
          <AlertHistoryList
            alerts={alerts}
            anomalies={anomalies}
            loading={isRefreshing}
            onTriggerTestAlert={handleTriggerTestAlert}
            isTestingAlert={isTestingAlert}
          />
        </section>
      </main>

      {/* 4. Modals */}
      <DemoScenarioSelector
        isOpen={isDemoSelectorOpen}
        onClose={() => setIsDemoSelectorOpen(false)}
        deviceId={deviceId}
        onScenarioInjected={() => {
          setIsDemoMode(true);
          fetchData();
        }}
      />

      <ModelStatusModal
        isOpen={isModelModalOpen}
        onClose={() => setIsModelModalOpen(false)}
        status={modelStatus}
        deviceId={deviceId}
        onRetrainSuccess={fetchData}
      />

      {/* 5. Footer */}
      <footer className="border-t border-forest-850 bg-forest-950 py-4 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            AI-Powered Multi-Sensor Environmental Monitoring &amp; Prediction System &bull; Phase 6 (Blynk IoT Enabled)
          </div>
          <div className="flex items-center gap-3 font-mono text-[11px]">
            <span>FastAPI: <strong className="text-slate-400">/api/v1/environment</strong></span>
            <span>&bull;</span>
            <span>Blynk Virtual Pins: <strong className="text-teal-400">V0–V7</strong></span>
            <span>&bull;</span>
            <span>Next.js 14 App Router</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
