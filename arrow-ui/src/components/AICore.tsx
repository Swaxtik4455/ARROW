import React, { useEffect, useRef } from "react";
import type { AssistantState } from "../types/arrow";

interface AICoreProps {
  state: AssistantState;
}

interface StateVisualConfig {
  primary: string;
  secondary: string;
  glow: string;
  accentRed: string;
  spinDurationSec: number;
  reverseSpinSec: number;
  pulseScale: number;
  particleSpeed: number;
  waveFrequency: number;
}

const STATE_CONFIG: Record<AssistantState, StateVisualConfig> = {
  IDLE: {
    primary: "#5ce1e6",
    secondary: "#164e63",
    glow: "rgba(92, 225, 230, 0.42)",
    accentRed: "#e05a47",
    spinDurationSec: 28,
    reverseSpinSec: 38,
    pulseScale: 1.03,
    particleSpeed: 0.35,
    waveFrequency: 0.012,
  },
  LISTENING: {
    primary: "#67f3f7",
    secondary: "#0e7490",
    glow: "rgba(103, 243, 247, 0.72)",
    accentRed: "#e05a47",
    spinDurationSec: 11,
    reverseSpinSec: 15,
    pulseScale: 1.09,
    particleSpeed: 1.15,
    waveFrequency: 0.03,
  },
  THINKING: {
    primary: "#38bdf8",
    secondary: "#0369a1",
    glow: "rgba(56, 189, 248, 0.78)",
    accentRed: "#f59e0b",
    spinDurationSec: 5.5,
    reverseSpinSec: 7.5,
    pulseScale: 1.06,
    particleSpeed: 1.85,
    waveFrequency: 0.042,
  },
  SPEAKING: {
    primary: "#7ef9ff",
    secondary: "#0891b2",
    glow: "rgba(126, 249, 255, 0.85)",
    accentRed: "#e05a47",
    spinDurationSec: 14,
    reverseSpinSec: 19,
    pulseScale: 1.13,
    particleSpeed: 1.35,
    waveFrequency: 0.036,
  },
  ERROR: {
    primary: "#e05a47",
    secondary: "#7f1d1d",
    glow: "rgba(224, 90, 71, 0.65)",
    accentRed: "#ef4444",
    spinDurationSec: 22,
    reverseSpinSec: 26,
    pulseScale: 1.04,
    particleSpeed: 0.5,
    waveFrequency: 0.02,
  },
  DISCONNECTED: {
    primary: "#334155",
    secondary: "#0f172a",
    glow: "rgba(51, 65, 85, 0.2)",
    accentRed: "#64748b",
    spinDurationSec: 90,
    reverseSpinSec: 110,
    pulseScale: 1.0,
    particleSpeed: 0.08,
    waveFrequency: 0.0,
  },
};

// Reusable subtle background radar node matching the reference screenshot
const BackgroundRadarNode: React.FC<{
  size: number;
  top?: string;
  bottom?: string;
  left?: string;
  right?: string;
}> = ({ size, top, bottom, left, right }) => {
  const c = size / 2;
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      style={{
        position: "absolute",
        top,
        bottom,
        left,
        right,
        opacity: 0.2,
        pointerEvents: "none",
      }}
    >
      <circle
        cx={c}
        cy={c}
        r={c - 4}
        fill="none"
        stroke="#5ce1e6"
        strokeWidth="1"
        strokeDasharray="2 5"
      />
      <circle
        cx={c}
        cy={c}
        r={c * 0.72}
        fill="none"
        stroke="#5ce1e6"
        strokeWidth="1.5"
        strokeDasharray="24 14"
      />
      <circle
        cx={c}
        cy={c}
        r={c * 0.45}
        fill="none"
        stroke="#5ce1e6"
        strokeWidth="1"
        strokeDasharray="3 4"
      />
    </svg>
  );
};

export const AICore: React.FC<AICoreProps> = ({ state }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const cfg = STATE_CONFIG[state];

  // Programmatic HTML5 Canvas particle & energy-wave layer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const size = 440;
    const center = size / 2;
    let animationId: number;
    let waveRadius = 56;
    let waveAlpha = 0.45;

    const particles = Array.from({ length: 22 }, (_, idx) => ({
      angle: (idx / 22) * Math.PI * 2,
      radius: 92 + (idx % 4) * 26,
      size: idx % 3 === 0 ? 2 : 1.3,
      dir: idx % 2 === 0 ? 1 : -1,
    }));

    const render = () => {
      ctx.clearRect(0, 0, size, size);

      // 1. Expanding subtle energy wave
      if (cfg.waveFrequency > 0) {
        waveRadius += 0.65 + cfg.waveFrequency * 24;
        waveAlpha -= 0.0045;
        if (waveRadius > 196 || waveAlpha <= 0) {
          waveRadius = 56;
          waveAlpha = state === "SPEAKING" || state === "LISTENING" ? 0.5 : 0.25;
        }

        ctx.beginPath();
        ctx.arc(center, center, waveRadius, 0, Math.PI * 2);
        ctx.strokeStyle = cfg.primary;
        ctx.globalAlpha = Math.max(0, waveAlpha);
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // 2. Orbiting micro-particles
      ctx.globalAlpha = state === "DISCONNECTED" ? 0.2 : 0.75;
      for (const p of particles) {
        p.angle += 0.006 * cfg.particleSpeed * p.dir;
        const x = center + Math.cos(p.angle) * p.radius;
        const y = center + Math.sin(p.angle) * p.radius;

        ctx.beginPath();
        ctx.arc(x, y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = cfg.primary;
        ctx.fill();
      }

      ctx.globalAlpha = 1;
      animationId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationId);
  }, [state, cfg]);

  // Generate 72 radial tick marks around the perimeter
  const ticks = Array.from({ length: 72 }, (_, i) => {
    const angle = (i * 360) / 72;
    const isMajor = i % 6 === 0;
    return (
      <line
        key={i}
        x1="220"
        y1={isMajor ? "52" : "56"}
        x2="220"
        y2="64"
        stroke={cfg.primary}
        strokeWidth={isMajor ? "1.4" : "0.8"}
        strokeOpacity={isMajor ? "0.7" : "0.35"}
        transform={`rotate(${angle} 220 220)`}
      />
    );
  });

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Subtle Ambient Background Radar Nodes (Matching Reference Image) */}
      <BackgroundRadarNode size={140} top="4%" left="13%" />
      <BackgroundRadarNode size={115} bottom="4%" left="19%" />

      {/* Main 440x440 Concentric Orb Container */}
      <div
        style={{
          position: "relative",
          width: 440,
          height: 440,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Canvas Particle & Energy Wave Layer */}
        <canvas
          ref={canvasRef}
          width={440}
          height={440}
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
          }}
        />

        {/* SVG Multi-Ring Mechanical & Telemetry HUD */}
        <svg
          width="440"
          height="440"
          viewBox="0 0 440 440"
          style={{
            position: "absolute",
            inset: 0,
            overflow: "visible",
          }}
        >
          <defs>
            <radialGradient id="arrowCoreGradient" cx="46%" cy="44%" r="54%">
              <stop offset="0%" stopColor="#e0fcff" stopOpacity="0.98" />
              <stop offset="32%" stopColor={cfg.primary} stopOpacity="0.88" />
              <stop offset="74%" stopColor={cfg.secondary} stopOpacity="0.72" />
              <stop offset="100%" stopColor="#04121c" stopOpacity="0.15" />
            </radialGradient>
            <filter id="hudGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Layer 1: Outermost Fine Dotted Boundary Ring */}
          <circle
            cx="220"
            cy="220"
            r="198"
            fill="none"
            stroke={cfg.primary}
            strokeWidth="1"
            strokeOpacity="0.28"
            strokeDasharray="1.5 6"
          />

          {/* Layer 2: Rotating Segmented Outer Cyan Arcs + Red Accent Segments */}
          <g
            style={{
              transformOrigin: "220px 220px",
              animation: `orbSpinCW ${cfg.spinDurationSec}s linear infinite`,
            }}
          >
            {/* Segmented Cyan Ring */}
            <circle
              cx="220"
              cy="220"
              r="182"
              fill="none"
              stroke={cfg.primary}
              strokeWidth="2.4"
              strokeOpacity="0.68"
              strokeDasharray="46 18 28 18 52 22"
              strokeLinecap="round"
            />
            {/* Opposing Red/Coral Telemetry Arcs (Signature Detail from Reference) */}
            <circle
              cx="220"
              cy="220"
              r="189"
              fill="none"
              stroke={cfg.accentRed}
              strokeWidth="2.6"
              strokeOpacity="0.9"
              strokeDasharray="34 560"
              strokeDashoffset="-48"
              strokeLinecap="round"
            />
            <circle
              cx="220"
              cy="220"
              r="189"
              fill="none"
              stroke={cfg.accentRed}
              strokeWidth="2.6"
              strokeOpacity="0.9"
              strokeDasharray="34 560"
              strokeDashoffset="-345"
              strokeLinecap="round"
            />
          </g>

          {/* Layer 3: Technical Radial Tick Scale */}
          <g
            style={{
              transformOrigin: "220px 220px",
              animation: `orbSpinCCW ${cfg.reverseSpinSec * 1.4}s linear infinite`,
            }}
          >
            {ticks}
          </g>

          {/* Layer 4: Middle Solid Precision Ring */}
          <circle
            cx="220"
            cy="220"
            r="146"
            fill="none"
            stroke={cfg.primary}
            strokeWidth="1.1"
            strokeOpacity="0.45"
          />

          {/* Layer 5: Rotating Dashed Orbital Ring */}
          <circle
            cx="220"
            cy="220"
            r="128"
            fill="none"
            stroke={cfg.primary}
            strokeWidth="1.6"
            strokeOpacity="0.6"
            strokeDasharray="3 7"
            style={{
              transformOrigin: "220px 220px",
              animation: `orbSpinCCW ${cfg.reverseSpinSec}s linear infinite`,
            }}
          />

          {/* Layer 6: Inner Containment Ring */}
          <circle
            cx="220"
            cy="220"
            r="96"
            fill="none"
            stroke={cfg.primary}
            strokeWidth="0.9"
            strokeOpacity="0.32"
          />

          {/* Layer 7: Central Illuminated Neural Sphere */}
          <g
            filter="url(#hudGlow)"
            style={{
              transformOrigin: "220px 220px",
              animation:
                state === "SPEAKING" || state === "LISTENING"
                  ? "corePulseActive 1.15s ease-in-out infinite alternate"
                  : state === "THINKING"
                    ? "corePulseFast 0.65s ease-in-out infinite alternate"
                    : "corePulseCalm 3.2s ease-in-out infinite alternate",
            }}
          >
            <circle
              cx="220"
              cy="220"
              r="58"
              fill="url(#arrowCoreGradient)"
              stroke={cfg.primary}
              strokeWidth="1.2"
              strokeOpacity="0.7"
            />
          </g>
        </svg>

        {/* Soft Ambient Outer Bloom */}
        <div
          style={{
            width: 120,
            height: 120,
            borderRadius: "50%",
            boxShadow: `0 0 65px 14px ${cfg.glow}`,
            pointerEvents: "none",
            transition: "box-shadow 0.4s ease",
          }}
        />
      </div>

      <style>{`
        @keyframes orbSpinCW {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes orbSpinCCW {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        @keyframes corePulseCalm {
          0% { transform: scale(0.98); opacity: 0.9; }
          100% { transform: scale(1.03); opacity: 1; }
        }
        @keyframes corePulseActive {
          0% { transform: scale(0.96); opacity: 0.92; }
          100% { transform: scale(1.11); opacity: 1; }
        }
        @keyframes corePulseFast {
          0% { transform: scale(0.95); opacity: 0.85; }
          100% { transform: scale(1.08); opacity: 1; }
        }
      `}</style>
    </div>
  );
};