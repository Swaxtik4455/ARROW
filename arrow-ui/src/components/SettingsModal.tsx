import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Volume2, Cpu, Trash2, Radio, Save } from "lucide-react";
import type { ArrowSettings } from "../types/arrow";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: ArrowSettings;
  backendConnected: boolean;
  wakeWordActive: boolean;
  onSaveSettings: (updated: Partial<ArrowSettings>) => void;
  onToggleWakeWord: () => void;
  onClearTranscript: () => void;
}

const MODES = ["normal", "detailed", "coding", "study", "professional"];

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  backendConnected,
  wakeWordActive,
  onSaveSettings,
  onToggleWakeWord,
  onClearTranscript,
}) => {
  const [draft, setDraft] = useState<ArrowSettings>(settings);
  const [savedNotice, setSavedNotice] = useState(false);

  // Sync draft when settings prop updates from backend
  React.useEffect(() => {
    setDraft(settings);
  }, [settings]);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onSaveSettings(draft);
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 1800);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          onClick={onClose}
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(2, 6, 12, 0.78)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "520px",
              maxWidth: "92vw",
              backgroundColor: "rgba(7, 17, 27, 0.96)",
              border: "1px solid var(--cyan-border-strong)",
              borderRadius: "6px",
              boxShadow:
                "0 0 40px rgba(0, 0, 0, 0.85), 0 0 24px rgba(92, 225, 230, 0.12)",
              padding: "22px 24px",
              color: "var(--text-primary)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {/* Header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                paddingBottom: "14px",
                borderBottom: "1px solid rgba(92, 225, 230, 0.16)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Cpu size={15} color="#5ce1e6" />
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 700,
                    letterSpacing: "0.24em",
                    color: "var(--cyan-primary)",
                  }}
                >
                  SYSTEM PARAMETERS
                </span>
              </div>

              <button
                onClick={onClose}
                style={{
                  background: "transparent",
                  border: "1px solid rgba(92, 225, 230, 0.25)",
                  color: "var(--text-secondary)",
                  width: 26,
                  height: 26,
                  borderRadius: "4px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                }}
              >
                <X size={14} />
              </button>
            </div>

            {/* Connection & Wake Word Quick Bar */}
            <div
              style={{
                marginTop: "14px",
                padding: "10px 12px",
                background: "rgba(4, 10, 18, 0.7)",
                border: "1px solid rgba(92, 225, 230, 0.15)",
                borderRadius: "4px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontSize: "11px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    backgroundColor: backendConnected ? "#5ce1e6" : "#e05a47",
                    boxShadow: backendConnected
                      ? "0 0 8px #5ce1e6"
                      : "0 0 8px #e05a47",
                  }}
                />
                <span style={{ letterSpacing: "0.1em" }}>
                  BRIDGE: {backendConnected ? "ONLINE (127.0.0.1)" : "OFFLINE"}
                </span>
              </div>

              <button
                type="button"
                onClick={onToggleWakeWord}
                style={{
                  background: wakeWordActive
                    ? "rgba(92, 225, 230, 0.2)"
                    : "rgba(15, 23, 42, 0.8)",
                  border: `1px solid ${
                    wakeWordActive
                      ? "var(--cyan-primary)"
                      : "rgba(92, 225, 230, 0.25)"
                  }`,
                  color: wakeWordActive
                    ? "var(--cyan-bright)"
                    : "var(--text-secondary)",
                  padding: "4px 10px",
                  borderRadius: "4px",
                  fontSize: "10px",
                  letterSpacing: "0.14em",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  cursor: "pointer",
                }}
              >
                <Radio size={11} />
                WAKE WORD: {wakeWordActive ? "ON" : "OFF"}
              </button>
            </div>

            {/* Settings Form */}
            <form
              onSubmit={handleSave}
              style={{
                marginTop: "16px",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
                fontSize: "11px",
              }}
            >
              {/* AI Persona Mode */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ color: "var(--text-secondary)", letterSpacing: "0.14em" }}>
                  AI RESPONSE PERSONA
                </label>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {MODES.map((m) => (
                    <button
                      type="button"
                      key={m}
                      onClick={() => setDraft({ ...draft, response_mode: m })}
                      style={{
                        padding: "5px 10px",
                        borderRadius: "4px",
                        fontSize: "10px",
                        letterSpacing: "0.14em",
                        textTransform: "uppercase",
                        cursor: "pointer",
                        background:
                          draft.response_mode === m
                            ? "rgba(92, 225, 230, 0.22)"
                            : "rgba(4, 10, 18, 0.65)",
                        border: `1px solid ${
                          draft.response_mode === m
                            ? "var(--cyan-primary)"
                            : "rgba(92, 225, 230, 0.18)"
                        }`,
                        color:
                          draft.response_mode === m
                            ? "var(--cyan-bright)"
                            : "var(--text-secondary)",
                      }}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>

              {/* Voice Engine & Windows SAPI5 Voice */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label style={{ color: "var(--text-secondary)", letterSpacing: "0.12em" }}>
                    VOICE SYNTHESIS
                  </label>
                  <select
                    value={draft.tts_engine}
                    onChange={(e) =>
                      setDraft({ ...draft, tts_engine: e.target.value })
                    }
                    style={{
                      background: "#050d16",
                      border: "1px solid var(--cyan-border)",
                      color: "var(--text-primary)",
                      padding: "6px 8px",
                      borderRadius: "4px",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                    }}
                  >
                    <option value="pyttsx3">Offline (pyttsx3)</option>
                    <option value="gtts">Online Neural (gTTS)</option>
                  </select>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label style={{ color: "var(--text-secondary)", letterSpacing: "0.12em" }}>
                    SYSTEM VOICE
                  </label>
                  <select
                    value={draft.voice_index}
                    onChange={(e) =>
                      setDraft({ ...draft, voice_index: Number(e.target.value) })
                    }
                    style={{
                      background: "#050d16",
                      border: "1px solid var(--cyan-border)",
                      color: "var(--text-primary)",
                      padding: "6px 8px",
                      borderRadius: "4px",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                    }}
                  >
                    {(draft.available_voices && draft.available_voices.length > 0
                      ? draft.available_voices
                      : ["Default System Voice"]
                    ).map((vName, idx) => (
                      <option key={idx} value={idx}>
                        {vName}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Speech Rate & Volume */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label style={{ color: "var(--text-secondary)", letterSpacing: "0.12em" }}>
                    SPEECH RATE: {draft.speech_rate} WPM
                  </label>
                  <input
                    type="range"
                    min={110}
                    max={250}
                    value={draft.speech_rate}
                    onChange={(e) =>
                      setDraft({ ...draft, speech_rate: Number(e.target.value) })
                    }
                    style={{ accentColor: "#5ce1e6" }}
                  />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label
                    style={{
                      color: "var(--text-secondary)",
                      letterSpacing: "0.12em",
                      display: "flex",
                      alignItems: "center",
                      gap: "5px",
                    }}
                  >
                    <Volume2 size={12} /> VOLUME: {Math.round(draft.speech_volume * 100)}%
                  </label>
                  <input
                    type="range"
                    min={0.1}
                    max={1}
                    step={0.05}
                    value={draft.speech_volume}
                    onChange={(e) =>
                      setDraft({ ...draft, speech_volume: Number(e.target.value) })
                    }
                    style={{ accentColor: "#5ce1e6" }}
                  />
                </div>
              </div>

              {/* Default City & Gemini Model */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label style={{ color: "var(--text-secondary)", letterSpacing: "0.12em" }}>
                    WEATHER LOCATION
                  </label>
                  <input
                    type="text"
                    value={draft.default_city}
                    onChange={(e) =>
                      setDraft({ ...draft, default_city: e.target.value })
                    }
                    style={{
                      background: "#050d16",
                      border: "1px solid var(--cyan-border)",
                      color: "var(--text-primary)",
                      padding: "6px 8px",
                      borderRadius: "4px",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      userSelect: "text",
                    }}
                  />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label style={{ color: "var(--text-secondary)", letterSpacing: "0.12em" }}>
                    GEMINI MODEL
                  </label>
                  <input
                    type="text"
                    value={draft.gemini_model}
                    onChange={(e) =>
                      setDraft({ ...draft, gemini_model: e.target.value })
                    }
                    style={{
                      background: "#050d16",
                      border: "1px solid var(--cyan-border)",
                      color: "var(--text-primary)",
                      padding: "6px 8px",
                      borderRadius: "4px",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      userSelect: "text",
                    }}
                  />
                </div>
              </div>

              {/* Footer Action Buttons */}
              <div
                style={{
                  marginTop: "10px",
                  paddingTop: "14px",
                  borderTop: "1px solid rgba(92, 225, 230, 0.14)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <button
                  type="button"
                  onClick={onClearTranscript}
                  style={{
                    background: "rgba(224, 90, 71, 0.14)",
                    border: "1px solid rgba(224, 90, 71, 0.45)",
                    color: "#fca5a5",
                    padding: "7px 12px",
                    borderRadius: "4px",
                    fontSize: "10px",
                    letterSpacing: "0.14em",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    cursor: "pointer",
                  }}
                >
                  <Trash2 size={12} /> CLEAR HISTORY
                </button>

                <button
                  type="submit"
                  style={{
                    background: "rgba(92, 225, 230, 0.2)",
                    border: "1px solid var(--cyan-primary)",
                    color: "var(--cyan-bright)",
                    padding: "7px 16px",
                    borderRadius: "4px",
                    fontSize: "10.5px",
                    fontWeight: 600,
                    letterSpacing: "0.16em",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    cursor: "pointer",
                  }}
                >
                  <Save size={12} />
                  {savedNotice ? "SAVED" : "APPLY CONFIG"}
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};