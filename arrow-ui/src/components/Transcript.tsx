import React, { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Settings, Send, Copy, Check } from "lucide-react";
import type { TranscriptEntry } from "../types/arrow";

interface TranscriptProps {
  messages: TranscriptEntry[];
  onSendCommand: (text: string) => void;
  onOpenSettings: () => void;
}

export const Transcript: React.FC<TranscriptProps> = ({
  messages,
  onSendCommand,
  onOpenSettings,
}) => {
  const [input, setInput] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;
    onSendCommand(trimmed);
    setInput("");
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <section
      style={{
        position: "relative",
        gridColumn: "2 / 3",
        gridRow: "1 / 2",
        backgroundColor: "var(--bg-panel)",
        border: "1px solid var(--cyan-border)",
        borderRadius: "6px",
        display: "flex",
        flexDirection: "column",
        backdropFilter: "blur(10px)",
        boxShadow:
          "0 0 28px rgba(0, 0, 0, 0.65), inset 0 0 20px rgba(92, 225, 230, 0.03)",
        minHeight: 0,
        zIndex: 15,
      }}
    >
      {/* Overlapping Top-Right Circular Settings Button */}
      <motion.button
        whileHover={{ scale: 1.08, rotate: 35 }}
        whileTap={{ scale: 0.94 }}
        onClick={onOpenSettings}
        title="System Parameters & Archive"
        style={{
          position: "absolute",
          top: -12,
          right: -12,
          width: 32,
          height: 32,
          borderRadius: "50%",
          backgroundColor: "#0a1522",
          border: "1px solid var(--cyan-border-strong)",
          color: "var(--cyan-primary)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          boxShadow: "0 0 12px rgba(92, 225, 230, 0.25)",
          zIndex: 20,
        }}
      >
        <Settings size={14} />
      </motion.button>

      {/* Panel Header */}
      <div
        style={{
          padding: "16px 20px 12px 20px",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          borderBottom: "1px solid rgba(92, 225, 230, 0.1)",
        }}
      >
        <span
          style={{
            width: 5,
            height: 5,
            borderRadius: "50%",
            backgroundColor: "var(--cyan-primary)",
            boxShadow: "0 0 6px var(--cyan-primary)",
          }}
        />
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            letterSpacing: "0.24em",
            color: "var(--cyan-primary)",
          }}
        >
          TRANSCRIPT
        </span>
      </div>

      {/* Scrollable Transcript Stream */}
      <div
        className="hud-scroll"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 20px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        {messages.map((msg) => {
          const isUser = msg.sender === "USR";
          const isSys = msg.sender === "SYS";
          return (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              style={{
                fontSize: "12.5px",
                lineHeight: 1.65,
                color: isUser ? "#f0f9ff" : isSys ? "#f59e0b" : "#cde6ee",
                wordBreak: "break-word",
                position: "relative",
              }}
            >
              <span
                style={{
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  color: isUser
                    ? "#64748b"
                    : isSys
                      ? "#e05a47"
                      : "var(--cyan-primary)",
                  marginRight: "10px",
                }}
              >
                {msg.sender}
              </span>
              <span style={{ whiteSpace: "pre-wrap" }}>{msg.text}</span>

              {!isUser && (
                <button
                  onClick={() => handleCopy(msg.id, msg.text)}
                  title="Copy response"
                  style={{
                    marginLeft: "8px",
                    background: "transparent",
                    border: "none",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    verticalAlign: "middle",
                    opacity: 0.65,
                  }}
                >
                  {copiedId === msg.id ? <Check size={11} /> : <Copy size={11} />}
                </button>
              )}
            </motion.div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Minimal HUD Command Input Bar */}
      <form
        onSubmit={handleSubmit}
        style={{
          padding: "10px 12px",
          borderTop: "1px solid rgba(92, 225, 230, 0.14)",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          background: "rgba(3, 8, 14, 0.55)",
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="ENTER COMMAND..."
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            color: "var(--text-primary)",
            fontFamily: "var(--font-mono)",
            fontSize: "11.5px",
            letterSpacing: "0.06em",
            userSelect: "text",
          }}
        />
        <button
          type="submit"
          title="Send Command"
          style={{
            background: "rgba(92, 225, 230, 0.1)",
            border: "1px solid var(--cyan-border)",
            color: "var(--cyan-primary)",
            width: 28,
            height: 26,
            borderRadius: "4px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
          }}
        >
          <Send size={12} />
        </button>
      </form>
    </section>
  );
};