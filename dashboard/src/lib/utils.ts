import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(val: number | null | undefined, decimals: number = 1, fallback: string = "--"): string {
  if (val === null || val === undefined || isNaN(val)) {
    return fallback;
  }
  return val.toFixed(decimals);
}

export function formatTime(isoString: string | null | undefined): string {
  if (!isoString) return "--:--:--";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "--:--:--";
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "--:--:--";
  }
}

export function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return "Never";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "Never";
    const sec = Math.floor((Date.now() - d.getTime()) / 1000);
    if (sec < 5) return "Just now";
    if (sec < 60) return `${sec}s ago`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min}m ago`;
    const hr = Math.floor(min / 60);
    return `${hr}h ago`;
  } catch {
    return "Unknown";
  }
}

export function getAirQualityLevel(voltage: number | null | undefined): {
  label: string;
  color: string;
  border: string;
  bg: string;
} {
  if (voltage === null || voltage === undefined) {
    return { label: "Unavailable", color: "text-slate-400", border: "border-slate-700", bg: "bg-slate-800/40" };
  }
  if (voltage < 1.0) {
    return { label: "Excellent", color: "text-emerald-400", border: "border-emerald-500/30", bg: "bg-emerald-950/30" };
  }
  if (voltage < 1.6) {
    return { label: "Moderate", color: "text-teal-300", border: "border-teal-500/30", bg: "bg-teal-950/30" };
  }
  if (voltage < 2.2) {
    return { label: "Poor", color: "text-amber-400", border: "border-amber-500/30", bg: "bg-amber-950/30" };
  }
  return { label: "Hazardous", color: "text-rose-400", border: "border-rose-500/30", bg: "bg-rose-950/30" };
}
