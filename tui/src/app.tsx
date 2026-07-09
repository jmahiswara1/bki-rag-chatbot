import React, { useState, useEffect, useCallback, useRef } from "react";
import { Box, Text, useApp, useInput } from "ink";
import Header from "./components/Header.js";
import ChatView from "./components/ChatView.js";
import InputBar from "./components/InputBar.js";
import type { MessageData } from "./components/Message.js";
import {
  BackendService,
  type BackendMessage,
  type Source,
} from "./services/backend.js";

interface AppProps {
  mode?: string;
}

const HELP_TEXT = `/help          show this help
/mode <name>   switch mode (default/fast)
/source        show sources of last answer
/clear         clear conversation
/exit          quit`;

export default function App({ mode = "default" }: AppProps) {
  const [currentMode, setCurrentMode] = useState(mode);
  const [model, setModel] = useState("qwen2.5:3b-instruct");
  const [messages, setMessages] = useState<MessageData[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [services, setServices] = useState({ ollama: false, supabase: false });
  const [escPressedOnce, setEscPressedOnce] = useState(false);
  const [lastResult, setLastResult] = useState<{
    sources?: Source[];
    timings?: Record<string, number>;
    language?: string;
    rejected?: boolean;
    rejectReason?: string;
  } | null>(null);

  const backendRef = useRef<BackendService | null>(null);
  const escTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { exit } = useApp();

  useEffect(() => {
    const backend = new BackendService();
    backendRef.current = backend;

    backend.on("token", (msg: BackendMessage) => {
      if (msg.type === "token") {
        setStreamingText((prev) => prev + msg.content);
      }
    });

    backend.on("done", (msg: BackendMessage) => {
      if (msg.type === "done") {
        const result: MessageData = {
          role: "assistant",
          content: msg.answer,
          timestamp: Date.now(),
          sources: msg.sources,
          timings: msg.timings,
          rejected: msg.rejected,
          reject_reason: msg.reject_reason,
          language: msg.language,
        };
        setMessages((prev) => [...prev, result]);
        setStreamingText("");
        setIsStreaming(false);
        setEscPressedOnce(false);
        setLastResult({
          sources: msg.sources,
          timings: msg.timings,
          language: msg.language,
          rejected: msg.rejected,
          rejectReason: msg.reject_reason,
        });
      }
    });

    backend.on("cancelled", () => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "[interrupted]", timestamp: Date.now() },
      ]);
      setStreamingText("");
      setIsStreaming(false);
      setEscPressedOnce(false);
    });

    backend.on("services", (msg: BackendMessage) => {
      if (msg.type === "services") {
        setServices({ ollama: msg.ollama, supabase: msg.supabase });
      }
    });

    backend.on("config", (msg: BackendMessage) => {
      if (msg.type === "config") {
        setModel(msg.model);
        setCurrentMode(msg.mode);
      }
    });

    backend.on("mode_changed", (msg: BackendMessage) => {
      if (msg.type === "mode_changed") {
        setCurrentMode(msg.content);
      }
    });

    backend.on("cleared", () => {
      setMessages([]);
      setLastResult(null);
    });

    backend.on("error", (msg: BackendMessage) => {
      if (msg.type === "error") {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `[error] ${msg.content}`, timestamp: Date.now() },
        ]);
        setStreamingText("");
        setIsStreaming(false);
        setEscPressedOnce(false);
      }
    });

    backend.waitReady().then(() => {
      backend.checkServices();
    });

    return () => {
      backend.close();
    };
  }, []);

  const handleSubmit = useCallback(
    (value: string) => {
      if (!value.trim()) return;

      // Handle slash commands
      if (value.startsWith("/")) {
        const parts = value.slice(1).split(/\s+/);
        const cmd = parts[0]?.toLowerCase();
        const arg = parts.slice(1).join(" ");

        if (cmd === "help") {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: HELP_TEXT, timestamp: Date.now() },
          ]);
          return;
        }

        if (cmd === "mode") {
          if (arg === "default" || arg === "fast") {
            backendRef.current?.setMode(arg);
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: `Mode changed to: ${arg}`, timestamp: Date.now() },
            ]);
          } else if (arg) {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: `Unknown mode: ${arg}`, timestamp: Date.now() },
            ]);
          } else {
            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: `Current mode: ${currentMode}`,
                timestamp: Date.now(),
              },
            ]);
          }
          return;
        }

        if (cmd === "source") {
          if (lastResult?.sources && lastResult.sources.length > 0) {
            const lines = lastResult.sources.map((s, i) => {
              const page =
                s.page_start === s.page_end
                  ? `p.${s.page_start}`
                  : `pp.${s.page_start}-${s.page_end}`;
              const citation = s.paragraph_id
                ? `(Sec ${s.section_no} | ${s.paragraph_id} ${page})`
                : `(Sec ${s.section_no}, ${page})`;
              const exc =
                s.content.length > 100
                  ? s.content.slice(0, 100) + "..."
                  : s.content;
              return `${i + 1}. ${citation}\n   ${exc}`;
            });
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: lines.join("\n"), timestamp: Date.now() },
            ]);
          } else {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: "(no sources yet)", timestamp: Date.now() },
            ]);
          }
          return;
        }

        if (cmd === "clear") {
          backendRef.current?.clear();
          return;
        }

        if (cmd === "exit" || cmd === "quit") {
          exit();
          return;
        }

        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Unknown command: /${cmd}`, timestamp: Date.now() },
        ]);
        return;
      }

      // Normal query
      setMessages((prev) => [...prev, { role: "user", content: value, timestamp: Date.now() }]);
      setIsStreaming(true);
      setStreamingText("");
      backendRef.current?.sendQuery(value, currentMode);
    },
    [currentMode, lastResult, exit]
  );

  const handleEscape = useCallback(() => {
    if (!isStreaming) return;

    if (!escPressedOnce) {
      // First ESC: show warning
      setEscPressedOnce(true);
      // Reset after 3 seconds
      if (escTimeoutRef.current) clearTimeout(escTimeoutRef.current);
      escTimeoutRef.current = setTimeout(() => {
        setEscPressedOnce(false);
        escTimeoutRef.current = null;
      }, 3000);
    } else {
      // Second ESC: cancel
      setEscPressedOnce(false);
      if (escTimeoutRef.current) {
        clearTimeout(escTimeoutRef.current);
        escTimeoutRef.current = null;
      }
      backendRef.current?.cancel();
    }
  }, [isStreaming, escPressedOnce]);

  useInput((inputChar, key) => {
    if (key.ctrl && inputChar === "c") {
      exit();
      return;
    }
    if (key.ctrl && inputChar === "l") {
      backendRef.current?.clear();
      return;
    }
  });

  return (
    <Box flexDirection="column">
      <Header mode={currentMode} model={model} />
      <ChatView
        messages={messages}
        streamingText={streamingText}
        isStreaming={isStreaming}
        escWarning={escPressedOnce}
      />
      <InputBar
        onSubmit={handleSubmit}
        onEscape={handleEscape}
        disabled={isStreaming}
        services={services}
      />
    </Box>
  );
}
