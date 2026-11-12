import React from "react";
import type { AssistantState } from "../types/arrow";

interface WaveformProps {
  state: AssistantState;
}

const BAR_COUNT = 34;

export const Waveform: React.FC<WaveformProps> = ({ state }) => {
  const isActive = state === "SPEAKING" || state === "LISTENING";
  const isThinking = state === "THINKING";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "4px",
        height: "28px",
      }}
      aria-label="Assistant Activity Waveform"
    >
      {Array.from({ length: BAR_COUNT }).map((_, i) => {
        const distFromCenter = Math.abs(i - BAR_COUNT / 2) / (BAR_COUNT / 2);
        const baseHeight = isActive
          ? Math.max(6, Math.round((1 - distFromCenter * 0.55) * 24))
          : isThinking
            ? 12
            : 16;

        return (
          <span
            key={i}
            style={{
              width: "2.5px",
              height: `${baseHeight}px`,
              borderRadius: "1px",
              backgroundColor:
                state === "ERROR"
                  ? "var(--red-accent)"
                  : isActive
                    ? "#5ce1e6"
                    : "rgba(92, 225, 230, 0.36)",
              boxShadow: isActive ? "0 0 6px rgba(92, 225, 230, 0.45)" : "none",
              transition: "height 0.25s ease, background-color 0.25s ease",
              animation: isActive
                ? `hudWave 0.75s ease-in-out ${(i % 7) * 0.09}s infinite alternate`
                : isThinking
                  ? `hudWave 1.1s ease-in-out ${(i % 5) * 0.14}s infinite alternate`
                  : "none",
            }}
          />
        );
      })}
      <style>{`
        @keyframes hudWave {
          0% { transform: scaleY(0.45); opacity: 0.55; }
          100% { transform: scaleY(1.15); opacity: 1; }
        }
      `}</style>
    </div>
  );
};