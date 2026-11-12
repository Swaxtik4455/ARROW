export type AssistantState =
  | "IDLE"
  | "LISTENING"
  | "THINKING"
  | "SPEAKING"
  | "ERROR"
  | "DISCONNECTED";

export interface TranscriptEntry {
  id: string;
  sender: "USR" | "ARROW" | "SYS";
  text: string;
  timestamp: string;
  category?: string;
}

export interface SystemTelemetry {
  cpuPercent: number;
  memPercent: number;
  backendConnected: boolean;
  activeMode: string;
  wakeWordActive: boolean;
}

export interface ArrowSettings {
  assistant_name: string;
  wake_word: string;
  gemini_model: string;
  response_mode: string;
  tts_engine: string;
  speech_rate: number;
  speech_volume: number;
  voice_index: number;
  default_city: string;
  available_voices?: string[];
}

declare global {
  interface Window {
    arrowDesktop?: {
      minimize: () => void;
      maximize: () => void;
      close: () => void;
      platform: string;
    };
  }
}