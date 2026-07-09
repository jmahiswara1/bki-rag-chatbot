import React from "react";
import { Box, Text } from "ink";

interface StatusBarProps {
  mode: string;
  language?: string;
  timings?: Record<string, number>;
  rejected?: boolean;
  rejectReason?: string;
}

export default function StatusBar({
  mode,
  language,
  timings,
  rejected,
  rejectReason,
}: StatusBarProps) {
  const parts: string[] = [`mode=${mode}`];
  if (language) parts.push(`lang=${language}`);

  if (timings) {
    const answerTime = timings["stream"] ?? timings["answer"];
    if (answerTime !== undefined) parts.push(`answer=${answerTime.toFixed(1)}s`);
    const totalTime = timings["total"];
    if (totalTime !== undefined) parts.push(`total=${totalTime.toFixed(1)}s`);
  }

  if (rejected) parts.push(`rejected: ${rejectReason}`);

  return (
    <Box
      borderStyle="single"
      borderColor="gray"
      paddingX={1}
      marginBottom={0}
    >
      <Text dimColor>{parts.join(" | ")}</Text>
    </Box>
  );
}
