import React, { useState, useCallback } from "react";
import { Box, Text, useInput } from "ink";
import TextInput from "./TextInput.js";

interface InputBarProps {
  onSubmit: (value: string) => void;
  onEscape?: () => void;
  disabled?: boolean;
  services?: { ollama: boolean; supabase: boolean };
}

const COMMANDS = [
  "/help",
  "/mode default",
  "/mode fast",
  "/source",
  "/clear",
  "/exit",
];

export default function InputBar({
  onSubmit,
  onEscape,
  disabled = false,
  services,
}: InputBarProps) {
  const [value, setValue] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [tempValue, setTempValue] = useState("");

  const handleSubmit = useCallback(
    (submitted: string) => {
      if (!submitted.trim()) return;
      setHistory((prev) => [...prev, submitted.trim()]);
      setHistoryIndex(-1);
      onSubmit(submitted.trim());
      setValue("");
    },
    [onSubmit]
  );

  // Hook 1: ESC handler (SELALU AKTIF - tidak terpengaruh disabled)
  useInput((inputChar, key) => {
    if (key.escape && onEscape) {
      onEscape();
    }
  });

  // Hook 2: History + Tab handler (hanya aktif saat tidak disabled)
  useInput(
    (inputChar, key) => {
      // History navigation (↑/↓)
      if (key.upArrow && history.length > 0) {
        const newIndex =
          historyIndex === -1
            ? history.length - 1
            : Math.max(0, historyIndex - 1);
        if (historyIndex === -1) setTempValue(value);
        setHistoryIndex(newIndex);
        setValue(history[newIndex]);
        return;
      }

      if (key.downArrow) {
        if (historyIndex === -1) return;
        const newIndex = historyIndex + 1;
        if (newIndex >= history.length) {
          setHistoryIndex(-1);
          setValue(tempValue);
        } else {
          setHistoryIndex(newIndex);
          setValue(history[newIndex]);
        }
        return;
      }

      // Command autocomplete (Tab)
      if (key.tab && value.startsWith("/")) {
        const matches = COMMANDS.filter((cmd) => cmd.startsWith(value));
        if (matches.length === 1) {
          setValue(matches[0]);
        } else if (matches.length > 1) {
          const common = matches.reduce((a, b) => {
            let i = 0;
            while (i < a.length && i < b.length && a[i] === b[i]) i++;
            return a.slice(0, i);
          });
          if (common.length > value.length) setValue(common);
        }
      }
    },
    { isActive: !disabled }
  );

  const borderColor = disabled ? "yellow" : "cyan";

  return (
    <Box
      borderStyle="round"
      borderColor={borderColor}
      paddingX={1}
      flexDirection="column"
    >
      <Box>
        <Text color="blue" bold>
          {">> "}
        </Text>
        <TextInput
          value={value}
          onChange={setValue}
          onSubmit={handleSubmit}
          placeholder={
            disabled
              ? "Waiting for response..."
              : "Type your question... (/help for commands)"
          }
          focus={!disabled}
        />
      </Box>
      {services && (
        <Box justifyContent="flex-end">
          <Text dimColor>
            <Text color={services.ollama ? "green" : "red"}>
              {services.ollama ? "●" : "○"} Ollama
            </Text>
            {"  "}
            <Text color={services.supabase ? "green" : "red"}>
              {services.supabase ? "●" : "○"} Vector DB
            </Text>
          </Text>
        </Box>
      )}
    </Box>
  );
}
