import React, { useRef, useEffect } from "react";
import { Box, Text } from "ink";
import { ScrollView, type ScrollViewRef } from "ink-scroll-view";
import Message, { StreamingMessage, type MessageData } from "./Message.js";

interface ChatViewProps {
  messages: MessageData[];
  streamingText: string;
  isStreaming: boolean;
  escWarning?: boolean;
}

export default function ChatView({
  messages,
  streamingText,
  isStreaming,
  escWarning = false,
}: ChatViewProps) {
  const scrollRef = useRef<ScrollViewRef>(null);

  useEffect(() => {
    // Auto-scroll when messages or streaming text changes
    scrollRef.current?.scrollToBottom();
  }, [messages, streamingText]);

  return (
    <Box flexDirection="column" flexGrow={1}>
      <ScrollView ref={scrollRef}>
        {messages.length === 0 && !isStreaming && (
          <Box paddingLeft={2} marginBottom={1}>
            <Text dimColor>
              Ask anything about BKI Hull Rules 2026. Type /help for commands.
            </Text>
          </Box>
        )}

        {messages.map((msg, i) => (
          <Message key={i} message={msg} />
        ))}

        {isStreaming && (
          <>
            <StreamingMessage text={streamingText} />
            {escWarning && (
              <Box paddingLeft={2}>
                <Text color="yellow">⚠ Press ESC again to interrupt</Text>
              </Box>
            )}
          </>
        )}
      </ScrollView>
    </Box>
  );
}
