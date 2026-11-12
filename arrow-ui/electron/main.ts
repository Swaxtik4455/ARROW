import { app, BrowserWindow, ipcMain } from "electron";
import { ChildProcess, spawn } from "child_process";
import fs from "fs";
import http from "http";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;

function resolveBackendPaths(): {
  pythonExec: string;
  bridgeScript: string;
  cwd: string;
} {
  // app.isPackaged is false during `npm run dev`, and true inside ARROW.exe
  const rootDir = !app.isPackaged
    ? path.resolve(__dirname, "../..")
    : path.join(process.resourcesPath, "backend");

  const venvPython = path.join(rootDir, ".venv", "Scripts", "python.exe");
  const pythonExec = fs.existsSync(venvPython) ? venvPython : "python";
  const bridgeScript = path.join(rootDir, "bridge", "bridge_server.py");

  return { pythonExec, bridgeScript, cwd: rootDir };
}

function startPythonBridge(): void {
  if (pythonProcess) return;
  const { pythonExec, bridgeScript, cwd } = resolveBackendPaths();

  if (!fs.existsSync(bridgeScript)) {
    console.error("Bridge script not found at:", bridgeScript);
    return;
  }

  pythonProcess = spawn(pythonExec, [bridgeScript], {
    cwd,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

  pythonProcess.stdout?.on("data", (data) => {
    console.log(`[ARROW Bridge]: ${data.toString().trim()}`);
  });

  pythonProcess.stderr?.on("data", (data) => {
    console.error(`[ARROW Bridge]: ${data.toString().trim()}`);
  });

  pythonProcess.on("exit", () => {
    pythonProcess = null;
  });
}

function stopPythonBridge(): void {
  if (pythonProcess && !pythonProcess.killed) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

function waitForBridge(retries = 25, delayMs = 300): Promise<void> {
  return new Promise((resolve) => {
    let attempts = 0;
    const check = () => {
      const req = http.get("http://127.0.0.1:8765/api/health", (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else if (++attempts < retries) {
          setTimeout(check, delayMs);
        } else {
          resolve();
        }
      });
      req.on("error", () => {
        if (++attempts < retries) {
          setTimeout(check, delayMs);
        } else {
          resolve();
        }
      });
    };
    check();
  });
}

async function createWindow(): Promise<void> {
  startPythonBridge();
  await waitForBridge();

  mainWindow = new BrowserWindow({
    width: 1380,
    height: 840,
    minWidth: 1120,
    minHeight: 700,
    backgroundColor: "#03060a",
    title: "ARROW — Voice Interface",
    frame: false,
    titleBarStyle: "hidden",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (!app.isPackaged) {
    await mainWindow.loadURL("http://localhost:5173");
  } else {
    const indexPath = path.join(app.getAppPath(), "dist", "index.html");
    await mainWindow.loadFile(indexPath);
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

ipcMain.on("window:minimize", () => mainWindow?.minimize());
ipcMain.on("window:maximize", () => {
  if (!mainWindow) return;
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow.maximize();
  }
});
ipcMain.on("window:close", () => mainWindow?.close());

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("before-quit", () => {
  stopPythonBridge();
});

app.on("window-all-closed", () => {
  stopPythonBridge();
  if (process.platform !== "darwin") {
    app.quit();
  }
});