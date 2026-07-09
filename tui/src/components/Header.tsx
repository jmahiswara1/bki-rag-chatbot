import React from "react";
import { Box, Text } from "ink";

interface HeaderProps {
  mode: string;
  model?: string;
}

export default function Header({ mode, model = "qwen2.5:3b-instruct" }: HeaderProps) {
  return (
    <Box
      borderStyle="round"
      borderColor="cyan"
      flexDirection="column"
      paddingX={1}
      marginBottom={1}
    >
      <Box>
        <Text bold color="cyan">
          BKI RAG Chatbot
        </Text>
        <Text dimColor> v1.0</Text>
      </Box>
      <Box>
        <Text dimColor>Model: {model} | Mode: </Text>
        <Text bold color="yellow">
          {mode}
        </Text>
      </Box>
    </Box>
  );
}
