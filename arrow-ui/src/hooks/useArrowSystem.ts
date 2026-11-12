import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ArrowSettings,
  AssistantState,
  SystemTelemetry,
  TranscriptEntry,
} from "../types/arrow";
import { arrowClient, WS_URL } from "../services/arrowClient";

const FALLBACK_SETTINGS: ArrowSettings = {
  assistant_name: "ARROW",
  wake_word: "arrow",
  gemini_model: "gemini-2.5-flash",
  response_mode: "normal",
  tts_engine: "pyttsx3",
  speech_rate: 180,
  speech_volume: 0.95,
  voice_index: 0,
  default_city: "Faizabad",
  available_voices: [],
};

export function useArrowSystem() {
  const [assistantState, setAssistantState] =
    useState<AssistantState>("DISCONNECTED");
  const [isMuted, setIsMuted] = useState(false);
  const [settings, setSettings] = useState<ArrowSettings>(FALLBACK_SETTINGS);
  const [messages, setMessages] = useState<TranscriptEntry[]>([]);
  const [telemetry, setTelemetry] = useState<SystemTelemetry>({
    cpuPercent: 0,
    memPercent: 0,
    backendConnected: false,
    activeMode: "normal",
    wakeWordActive: false,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  // Load persisted history & settings once connected
  const syncInitialData = useCallback(async () => {
    try {
      const [loadedSettings, history] = await Promise.all([
        arrowClient.getSettings(),
        arrowClient.getHistory(25),
      ]);
      setSettings(loadedSettings);
      setTelemetry((prev) => ({
        ...prev,
        activeMode: loadedSettings.response_mode || "normal",
      }));

      if (history.length > 0) {
        const mapped: TranscriptEntry[] = history.map((m) => ({
          id: m.id,
          sender: m.role === "user" ? "USR" : "ARROW",
          text: m.content,
          timestamp: m.timestamp.slice(11, 16) || "",
        }));
        setMessages(mapped);
      } else {
        setMessages([
          {
            id: "welcome",
            sender: "ARROW",
            text: "ARROW neural core online. All subsystems operational. Speak or enter a command.",
            timestamp: new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
          },
        ]);
      }
    } catch {
      // Handled by WebSocket retry loop
    }
  }, []);

  // Auto-reconnecting WebSocket connection to Python Bridge
  useEffect(() => {
    let unmounted = false;

    const connect = () => {
      if (unmounted) return;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (unmounted) return;
        setTelemetry((prev) => ({ ...prev, backendConnected: true }));
        setAssistantState("IDLE");
        syncInitialData();
      };

      ws.onmessage = (event) => {
        if (unmounted) return;
        try {
          const data = JSON.parse(event.data);

          if (data.type === "state") {
            setAssistantState(data.state as AssistantState);
            if (typeof data.isMuted === "boolean") setIsMuted(data.isMuted);
            if (typeof data.wakeWordActive === "boolean") {
              setTelemetry((prev) => ({
                ...prev,
                wakeWordActive: data.wakeWordActive,
              }));
            }
          } else if (data.type === "telemetry") {
            setTelemetry((prev) => ({
              ...prev,
              cpuPercent: data.cpuPercent ?? prev.cpuPercent,
              memPercent: data.memPercent ?? prev.memPercent,
              activeMode: data.activeMode ?? prev.activeMode,
              wakeWordActive: data.wakeWordActive ?? prev.wakeWordActive,
            }));
          } else if (data.type === "transcript") {
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                sender: data.sender,
                text: data.text,
                timestamp: data.timestamp || "",
                category: data.category,
              },
            ]);
          }
        } catch {
          // Ignore malformed frame
        }
      };

      ws.onclose = () => {
        if (unmounted) return;
        setTelemetry((prev) => ({ ...prev, backendConnected: false }));
        setAssistantState("DISCONNECTED");
        reconnectTimerRef.current = window.setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      unmounted = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [syncInitialData]);

  // Action Handlers
  const sendCommand = useCallback(
    async (text: string) => {
      const now = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), sender: "USR", text, timestamp: now },
      ]);
      try {
        await arrowClient.sendCommand(text, !isMuted);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            sender: "SYS",
            text: `Unable to reach Python bridge: ${err instanceof Error ? err.message : "offline"}`,
            timestamp: now,
          },
        ]);
      }
    },
    [isMuted]
  );

  const triggerMic = useCallback(async () => {
    try {
      await arrowClient.triggerListen();
    } catch {
      setAssistantState("ERROR");
    }
  }, []);

  const toggleMute = useCallback(async () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    try {
      await arrowClient.setMute(nextMuted);
    } catch {
      // Revert if offline
      setIsMuted(!nextMuted);
    }
  }, [isMuted]);

  const interrupt = useCallback(async () => {
    try {
      await arrowClient.interruptSpeech();
    } catch {
      setAssistantState("IDLE");
    }
  }, []);

  const toggleWakeWord = useCallback(async () => {
    const nextWake = !telemetry.wakeWordActive;
    try {
      const res = await arrowClient.setWakeWord(nextWake);
      setTelemetry((prev) => ({
        ...prev,
        wakeWordActive: Boolean(res.wakeWordActive),
      }));
    } catch {
      // Ignore if offline
    }
  }, [telemetry.wakeWordActive]);

  const saveSettings = useCallback(async (updates: Partial<ArrowSettings>) => {
    const updated = await arrowClient.updateSettings(updates);
    setSettings(updated);
    setTelemetry((prev) => ({
      ...prev,
      activeMode: updated.response_mode || prev.activeMode,
    }));
  }, []);

  const clearHistory = useCallback(async () => {
    await arrowClient.clearHistory();
    setMessages([]);
  }, []);

  return {
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
  };
}