import React from "react";
import type { SystemTelemetry } from "../types/arrow";

interface GaugeProps {
  label: string;
  value: number;
  size?: number;
}

const CircularGauge: React.FC<GaugeProps> = ({ label, value, size = 66 }) => {
  const strokeWidth = 2.5;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, value));
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <div
      style={{
        position: "relative",
        width: size,
        height: size,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      title={`${label}: ${clamped}%`}
    >
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="rgba(5, 13, 22, 0.45)"
          stroke="rgba(92, 225, 230, 0.16)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="transparent"
          stroke="#5ce1e6"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{
            transition: "stroke-dashoffset 0.5s ease",
            filter: "drop-shadow(0 0 4px rgba(92, 225, 230, 0.5))",
          }}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span
          style={{
            fontSize: "9px",
            letterSpacing: "0.18em",
            color: "var(--text-secondary)",
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            color: "var(--cyan-primary)",
            marginTop: "1px",
          }}
        >
          {Math.round(clamped)}%
        </span>
      </div>
    </div>
  );
};

interface TelemetryProps {
  telemetry: SystemTelemetry;
}

export const Telemetry: React.FC<TelemetryProps> = ({ telemetry }) => {
  return (
    <aside
      style={{
        position: "absolute",
        left: 68,
        top: "33%",
        display: "flex",
        flexDirection: "column",
        gap: "88px",
        zIndex: 10,
      }}
    >
      <CircularGauge label="CPU" value={telemetry.cpuPercent} size={68} />
      <div style={{ marginLeft: "18px" }}>
        <CircularGauge label="MEM" value={telemetry.memPercent} size={62} />
      </div>
    </aside>
  );
};