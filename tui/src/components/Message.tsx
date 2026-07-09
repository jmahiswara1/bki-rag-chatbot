import React from "react";
import { Box, Text } from "ink";
import Spinner from "./Spinner.js";

interface Source {
  section_no: number;
  section_title: string;
  paragraph_id: string;
  page_start: number;
  page_end: number;
  content: string;
  content_type: string;
}

export interface MessageData {
  role: "user" | "assistant";
  content: string;
  timestamp?: number;
  sources?: Source[];
  timings?: Record<string, number>;
  rejected?: boolean;
  reject_reason?: string;
  language?: string;
  terminalWidth?: number;
}

interface MessageProps {
  message: MessageData;
}

function formatTime(ts?: number): string {
  if (!ts) return "";
  const date = new Date(ts);
  return date.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
}

function formatPage(s: Source): string {
  if (s.page_start === s.page_end) return `p.${s.page_start}`;
  return `pp.${s.page_start}-${s.page_end}`;
}

function formatCitation(s: Source): string {
  const page = formatPage(s);
  if (s.paragraph_id) return `(Sec ${s.section_no} | ${s.paragraph_id} ${page})`;
  return `(Sec ${s.section_no}, ${page})`;
}

function SourcePanel({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null;

  return (
    <Box
      flexDirection="column"
      marginTop={1}
      paddingLeft={4}
      paddingRight={2}
      borderStyle="single"
      borderColor="cyan"
    >
      {/* Header */}
      <Box marginBottom={1}>
        <Text color="cyan" bold>
          Sources ({sources.length})
        </Text>
      </Box>

      {/* Sources */}
      {sources.map((s, i) => {
        const citation = formatCitation(s);

        return (
          <Box key={i} flexDirection="column" marginBottom={i < sources.length - 1 ? 1 : 0}>
            {/* Citation */}
            <Box>
              <Text bold color="cyan">
                {i + 1}.{" "}
              </Text>
              <Text color="magenta">{citation}</Text>
            </Box>
            {/* Content */}
            <Box paddingLeft={3}>
              <Text dimColor wrap="wrap">
                {s.content}
              </Text>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}

function FooterInfo({ message }: { message: MessageData }) {
  if (!message.timings) return null;

  const parts: string[] = [];
  if (message.language) parts.push(`lang=${message.language}`);

  const answerTime = message.timings["stream"] ?? message.timings["answer"];
  if (answerTime !== undefined) parts.push(`answer=${answerTime.toFixed(1)}s`);

  const totalTime = message.timings["total"];
  if (totalTime !== undefined) parts.push(`total=${totalTime.toFixed(1)}s`);

  if (message.rejected) parts.push(`rejected: ${message.reject_reason}`);

  if (parts.length === 0) return null;

  return (
    <Box paddingLeft={4} marginTop={0}>
      <Text dimColor>{parts.join(" | ")}</Text>
    </Box>
  );
}

export default function Message({ message }: MessageProps) {
  if (message.role === "user") {
    return (
      <Box flexDirection="column" marginBottom={1}>
        <Box paddingLeft={2}>
          <Text bold color="blue">
            {">> You"}
          </Text>
          <Text dimColor> {formatTime(message.timestamp)}</Text>
        </Box>
        <Box paddingLeft={4}>
          <Text>{message.content}</Text>
        </Box>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box paddingLeft={2}>
        <Text bold color="green">
          {">> BKI"}
        </Text>
        <Text dimColor> {formatTime(message.timestamp)}</Text>
      </Box>
      <Box paddingLeft={4} flexDirection="column">
        <Text>{message.content}</Text>
      </Box>
      {message.sources && <SourcePanel sources={message.sources} />}
      <FooterInfo message={message} />
    </Box>
  );
}

export function StreamingMessage({ text }: { text: string }) {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box paddingLeft={2}>
        <Text bold color="green">
          {">> BKI "}
        </Text>
        <Spinner color="green" />
      </Box>
      <Box paddingLeft={4}>
        <Text>{text || "thinking..."}</Text>
      </Box>
    </Box>
  );
}
