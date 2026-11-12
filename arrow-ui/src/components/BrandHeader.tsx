import React from "react";

export const BrandHeader: React.FC = () => {
  return (
    <div
      className="bracket-box"
      style={{
        position: "absolute",
        top: 22,
        left: 28,
        padding: "6px 14px",
        zIndex: 10,
      }}
    >
      <h1
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "30px",
          fontWeight: 700,
          letterSpacing: "0.34em",
          color: "#f0f9ff",
          lineHeight: 1.05,
          textShadow: "0 0 18px rgba(92, 225, 230, 0.35)",
        }}
      >
        ARROW
      </h1>
      <p
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "10px",
          fontWeight: 500,
          letterSpacing: "0.28em",
          color: "var(--cyan-primary)",
          marginTop: "5px",
          opacity: 0.85,
        }}
      >
        VOICE INTERFACE
      </p>
    </div>
  );
};