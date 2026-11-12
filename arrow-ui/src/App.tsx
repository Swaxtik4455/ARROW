import { useEffect, useState } from "react";
import "./index.css";
import { useArrowSystem } from "./hooks/useArrowSystem";
import { TitleBar } from "./components/TitleBar";
import { BrandHeader } from "./components/BrandHeader";
import { Telemetry } from "./components/Telemetry";
import { AICore } from "./components/AICore";
import { Transcript } from "./components/Transcript";
import { Controls } from "./components/Controls";
import { SettingsModal } from "./components/SettingsModal";

export function App() {
  const {
    assistantState,
    isMuted,
    settings,
    messages,
    telemetry,
    sendCommand,
    triggerMic,
    toggleMute,
    interrupt,
    toggleWakeWord,
    saveSettings,
    clearHistory,
  } = useArrowSystem();

  const [settingsOpen, setSettingsOpen] = useState(false);

  // Global keyboard shortcuts: Escape (interrupt/close modal), Ctrl+M (mute)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (settingsOpen) {
          setSettingsOpen(false);
        } else if (assistantState === "SPEAKING") {
          interrupt();
        }
      } else if (e.ctrlKey && e.key.toLowerCase() === "m") {
        e.preventDefault();
        toggleMute();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [settingsOpen, assistantState, interrupt, toggleMute]);

  return (
    <div className="hud-canvas">
      <TitleBar connected={telemetry.backendConnected} />

      <main className="hud-workspace">
        {/* Region A: Top-Left ARROW Branding */}
        <BrandHeader />

        {/* Region D: Left-Side Circular CPU & MEM Telemetry (Real Live Metrics) */}
        <Telemetry telemetry={telemetry} />

        {/* Region B: Central Multi-Layered Animated AI Core */}
        <div
          onClick={triggerMic}
          title="Click Core to Activate Microphone"
          style={{
            gridColumn: "1 / 2",
            gridRow: "1 / 2",
            position: "relative",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
          }}
        >
          <AICore state={assistantState} />
        </div>

        {/* Region C: Right-Side Live Transcript Panel */}
        <Transcript
          messages={messages}
          onSendCommand={sendCommand}
          onOpenSettings={() => setSettingsOpen(true)}
        />

        {/* Region E: Bottom Status, Waveform, Mute & Interrupt Controls */}
        <Controls
          state={assistantState}
          isMuted={isMuted}
          onToggleMic={triggerMic}
          onToggleMute={toggleMute}
          onInterrupt={interrupt}
        />
      </main>

      {/* Settings & System Parameters Overlay */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        backendConnected={telemetry.backendConnected}
        wakeWordActive={telemetry.wakeWordActive}
        onSaveSettings={saveSettings}
        onToggleWakeWord={toggleWakeWord}
        onClearTranscript={clearHistory}
      />
    </div>
  );
}

export default App;