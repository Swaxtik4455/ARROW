import type { ArrowSettings } from "../types/arrow";

const API_BASE = "http://127.0.0.1:8765";
export const WS_URL = "ws://127.0.0.1:8765/ws";

export interface StoredMessage {
  id: string;
  timestamp: string;
  role: "user" | "assistant";
  mode?: string;
  content: string;
}

export const arrowClient = {
  async checkHealth() {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error("Bridge health check failed");
    return res.json();
  },

  async sendCommand(text: string, speak: boolean = true) {
    const res = await fetch(`${API_BASE}/api/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, speak }),
    });
    if (!res.ok) throw new Error(`Command failed (${res.status})`);
    return res.json();
  },

  async triggerListen() {
    const res = await fetch(`${API_BASE}/api/voice/listen`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to trigger microphone");
    return res.json();
  },

  async setWakeWord(enabled: boolean) {
    const res = await fetch(`${API_BASE}/api/voice/wake`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    if (!res.ok) throw new Error("Failed to toggle wake word");
    return res.json();
  },

  async setMute(muted: boolean) {
    const res = await fetch(`${API_BASE}/api/voice/mute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ muted }),
    });
    if (!res.ok) throw new Error("Failed to toggle mute");
    return res.json();
  },

  async interruptSpeech() {
    const res = await fetch(`${API_BASE}/api/voice/interrupt`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to interrupt speech");
    return res.json();
  },

  async getSettings(): Promise<ArrowSettings> {
    const res = await fetch(`${API_BASE}/api/settings`);
    if (!res.ok) throw new Error("Failed to load settings");
    return res.json();
  },

  async updateSettings(updates: Partial<ArrowSettings>): Promise<ArrowSettings> {
    const res = await fetch(`${API_BASE}/api/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ updates }),
    });
    if (!res.ok) throw new Error("Failed to save settings");
    return res.json();
  },

  async getHistory(limit: number = 30): Promise<StoredMessage[]> {
    const res = await fetch(`${API_BASE}/api/history?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch history");
    const data = await res.json();
    return data.messages || [];
  },

  async clearHistory() {
    const res = await fetch(`${API_BASE}/api/history`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to clear history");
    return res.json();
  },
};