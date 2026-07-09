import { spawn, type ChildProcess } from "node:child_process";
import { createInterface } from "node:readline";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export interface Source {
  section_no: number;
  section_title: string;
  paragraph_id: string;
  page_start: number;
  page_end: number;
  content: string;
  content_type: string;
}

export interface DoneMessage {
  type: "done";
  answer: string;
  sources: Source[];
  language: string;
  rejected: boolean;
  reject_reason: string;
  timings: Record<string, number>;
}

export interface ServicesMessage {
  type: "services";
  ollama: boolean;
  supabase: boolean;
}

export interface ConfigMessage {
  type: "config";
  model: string;
  mode: string;
}

export type BackendMessage =
  | { type: "status"; content: string }
  | { type: "token"; content: string }
  | DoneMessage
  | ServicesMessage
  | ConfigMessage
  | { type: "mode_changed"; content: string }
  | { type: "cleared" }
  | { type: "error"; content: string }
  | { type: "ready" }
  | { type: "pong" };

export type BackendHandler = (msg: BackendMessage) => void;

export class BackendService {
  private process: ChildProcess;
  private rl: ReturnType<typeof createInterface>;
  private handlers: Map<string, BackendHandler[]> = new Map();
  private ready = false;
  private readyResolve: (() => void) | null = null;
  private readyPromise: Promise<void>;

  constructor() {
    const bridgePath = path.join(__dirname, "..", "..", "python", "bridge.py");
    const projectRoot = path.join(__dirname, "..", "..");

    this.process = spawn("python", [bridgePath], {
      stdio: ["pipe", "pipe", "pipe"],
      cwd: projectRoot,
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
      },
    });

    this.rl = createInterface({ input: this.process.stdout! });

    this.readyPromise = new Promise((resolve) => {
      this.readyResolve = resolve;
    });

    this.rl.on("line", (line: string) => {
      try {
        const msg = JSON.parse(line) as BackendMessage;
        if (msg.type === "ready") {
          this.ready = true;
          this.readyResolve?.();
        }
        this.dispatch(msg);
      } catch {
        // ignore parse errors
      }
    });

    let stderrBuffer = "";
    this.process.stderr?.on("data", (data: Buffer) => {
      stderrBuffer += data.toString();
      // Only log if there's actual content
      const trimmed = stderrBuffer.trim();
      if (trimmed) {
        process.stderr.write(`[bridge] ${trimmed}\n`);
        stderrBuffer = "";
      }
    });

    this.process.on("exit", (code: number | null) => {
      if (code !== 0 && code !== null) {
        this.dispatch({
          type: "error",
          content: `Bridge exited with code ${code}`,
        });
      }
    });
  }

  on(type: string, handler: BackendHandler): void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);
  }

  off(type: string, handler: BackendHandler): void {
    const list = this.handlers.get(type);
    if (list) {
      const idx = list.indexOf(handler);
      if (idx !== -1) list.splice(idx, 1);
    }
  }

  private dispatch(msg: BackendMessage): void {
    const list = this.handlers.get(msg.type);
    if (list) {
      for (const handler of list) {
        handler(msg);
      }
    }
  }

  async waitReady(): Promise<void> {
    if (this.ready) return;
    await this.readyPromise;
  }

  send(msg: object): void {
    this.process.stdin!.write(JSON.stringify(msg) + "\n");
  }

  sendQuery(content: string, mode?: string): void {
    this.send({ type: "query", content, ...(mode ? { mode } : {}) });
  }

  setMode(mode: string): void {
    this.send({ type: "mode", content: mode });
  }

  clear(): void {
    this.send({ type: "clear" });
  }

  checkServices(): void {
    this.send({ type: "check_services" });
  }

  cancel(): void {
    this.send({ type: "cancel" });
  }

  close(): void {
    try {
      this.send({ type: "exit" });
    } catch {
      // ignore
    }
    try {
      this.process.kill();
    } catch {
      // ignore
    }
  }
}
