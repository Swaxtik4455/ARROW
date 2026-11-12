import React from "react";
import { Minus, Square, X } from "lucide-react";

interface TitleBarProps {
  connected: boolean;
}

export const TitleBar: React.FC<TitleBarProps> = ({ connected }) => {
  return (
    <header className="titlebar">
      <div className="titlebar-label">
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            backgroundColor: connected ? "#5ce1e6" : "#e05a47",
            boxShadow: connected ? "0 0 8px #5ce1e6" : "0 0 8px #e05a47",
          }}
        />
        <span>ARROW // HUD OS v1.0</span>
      </div>

      <div className="titlebar-controls">
        <button
          className="win-btn"
          title="Minimize"
          onClick={() => window.arrowDesktop?.minimize()}
        >
          <Minus size={12} />
        </button>
        <button
          className="win-btn"
          title="Maximize"
          onClick={() => window.arrowDesktop?.maximize()}
        >
          <Square size={10} />
        </button>
        <button
          className="win-btn close"
          title="Close"
          onClick={() => window.arrowDesktop?.close()}
        >
          <X size={13} />
        </button>
      </div>
    </header>
  );
};