import React from "react";
import type { AssistantState } from "../types/arrow";
import { Waveform } from "./Waveform";

interface ControlsProps {
  state: AssistantState;
  isMuted: boolean;
  onToggleMic: () => void;
  onToggleMute: () => void;
  onInterrupt: () => void;
}

export const Controls: React.FC<ControlsProps> = ({
  state,
  isMuted,
  onToggleMic,
  onToggleMute,
  onInterrupt,
}) => {
  const statusTextMap: Record<AssistantState, string> = {
    IDLE: "STANDBY READY",
    LISTENING: "LISTENING...",
    THINKING: "PROCESSING...",
    SPEAKING: "SPEAKING...",
    ERROR: "SYSTEM ALERT",
    DISCONNECTED: "BRIDGE OFFLINE",
  };

  const dotColor =
    state === "ERROR" || state === "DISCONNECTED"
      ? "var(--red-accent)"
      : "var(--cyan-primary)";

  return (
    <>
      {/* Bottom-Left Status Indicator + Bottom-Center Waveform */}
      <div
        style={{
          gridColumn: "1 / 2",
          gridRow: "2 / 3",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          paddingRight: "24px",
        }}
      >
        {/* Corner-Bracketed Status Readout (Clickable for Push-to-Talk Mic) */}
        <button
          onClick={onToggleMic}
          title="Click to Trigger Voice Listening"
          className="bracket-box"
          style={{
            background: "transparent",
            border: "none",
            padding: "8px 14px",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            cursor: "pointer",
            color: "var(--text-primary)",
            fontFamily: "var(--font-mono)",
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              backgroundColor: dotColor,
              boxShadow: `0 0 10px ${dotColor}`,
            }}
          />
          <span
            style={{
              fontSize: "11px",
              fontWeight: 600,
              letterSpacing: "0.24em",
            }}
          >
            {statusTextMap[state]}
          </span>
        </button>

        {/* Center Equalizer Waveform */}
        <Waveform state={state} />

        {/* Right spacer to keep waveform visually centered under the AI Core */}
        <div style={{ width: 90 }} />
      </div>

      {/* Bottom-Right MUTE & INTERRUPT Buttons Aligned Under Transcript */}
      <div
        style={{
          gridColumn: "2 / 3",
          gridRow: "2 / 3",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "10px",
        }}
      >
        <button
          onClick={onToggleMute}
          style={{
            height: "38px",
            backgroundColor: isMuted
              ? "rgba(224, 90, 71, 0.16)"
              : "var(--bg-panel)",
            border: `1px solid ${isMuted ? "rgba(224, 90, 71, 0.65)" : "var(--cyan-border)"}`,
            borderRadius: "4px",
            color: isMuted ? "#fca5a5" : "var(--text-primary)",
            fontFamily: "var(--font-mono)",
            fontSize: "10.5px",
            fontWeight: 600,
            letterSpacing: "0.22em",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
        >
          {isMuted ? "MUTED" : "MUTE"}
        </button>

        <button
          onClick={onInterrupt}
          style={{
            height: "38px",
            backgroundColor:
              state === "SPEAKING"
                ? "rgba(92, 225, 230, 0.14)"
                : "var(--bg-panel)",
            border: `1px solid ${
              state === "SPEAKING"
                ? "var(--cyan-border-strong)"
                : "var(--cyan-border)"
            }`,
            borderRadius: "4px",
            color:
              state === "SPEAKING"
                ? "var(--cyan-bright)"
                : "var(--text-secondary)",
            fontFamily: "var(--font-mono)",
            fontSize: "10.5px",
            fontWeight: 600,
            letterSpacing: "0.2em",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
        >
          {state === "SPEAKING" ? "INTERRUPT" : "INTERRUPT OFF"}
        </button>
      </div>
    </>
  );
};