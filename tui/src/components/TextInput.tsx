import React, { useState, useEffect } from "react";
import { Text, useInput } from "ink";
import chalk from "chalk";

interface TextInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: (value: string) => void;
  placeholder?: string;
  focus?: boolean;
  mask?: string;
  showCursor?: boolean;
  highlightPastedText?: boolean;
}

export default function TextInput({
  value: originalValue,
  placeholder = "",
  focus = true,
  mask,
  highlightPastedText = false,
  showCursor = true,
  onChange,
  onSubmit,
}: TextInputProps) {
  const [state, setState] = useState({
    cursorOffset: (originalValue || "").length,
    cursorWidth: 0,
  });
  const { cursorOffset, cursorWidth } = state;

  useEffect(() => {
    setState((previousState) => {
      if (!focus || !showCursor) return previousState;
      const newValue = originalValue || "";
      if (previousState.cursorOffset > newValue.length - 1) {
        return { cursorOffset: newValue.length, cursorWidth: 0 };
      }
      return previousState;
    });
  }, [originalValue, focus, showCursor]);

  const cursorActualWidth = highlightPastedText ? cursorWidth : 0;
  const value = mask ? mask.repeat(originalValue.length) : originalValue;

  useInput(
    (input, key) => {
      // Ignore keys yang tidak perlu diproses
      if (
        key.upArrow ||
        key.downArrow ||
        (key.ctrl && input === "c") ||
        key.tab ||
        (key.shift && key.tab)
      ) {
        return;
      }

      // Submit
      if (key.return) {
        if (onSubmit) onSubmit(originalValue);
        return;
      }

      let nextCursorOffset = cursorOffset;
      let nextValue = originalValue;
      let nextCursorWidth = 0;

      if (key.leftArrow) {
        if (showCursor) nextCursorOffset--;
      } else if (key.rightArrow) {
        if (showCursor) nextCursorOffset++;
      } else if (key.home) {
        nextCursorOffset = 0;
      } else if (key.end) {
        nextCursorOffset = originalValue.length;
      }
      else if (key.ctrl && key.backspace) {
        // Ctrl+Backspace: Hapus kata sebelum cursor
        const beforeCursor = originalValue.slice(0, cursorOffset);
        const afterCursor = originalValue.slice(cursorOffset);
        const trimmed = beforeCursor.trimEnd();
        const lastSpace = trimmed.lastIndexOf(" ");
        if (lastSpace === -1) {
          nextValue = afterCursor;
          nextCursorOffset = 0;
        } else {
          nextValue = trimmed.slice(0, lastSpace + 1) + afterCursor;
          nextCursorOffset = lastSpace + 1;
        }
      } else if (key.ctrl && key.delete) {
        // Ctrl+Delete: Hapus kata setelah cursor
        const beforeCursor = originalValue.slice(0, cursorOffset);
        const afterCursor = originalValue.slice(cursorOffset);
        const trimmed = afterCursor.trimStart();
        const firstSpace = trimmed.indexOf(" ");
        if (firstSpace === -1) {
          nextValue = beforeCursor;
        } else {
          nextValue = beforeCursor + trimmed.slice(firstSpace);
        }
        nextCursorOffset = cursorOffset;
      } else if (key.ctrl && (input === "u" || input === "U")) {
        // Ctrl+U: Hapus seluruh baris
        nextValue = "";
        nextCursorOffset = 0;
      } else if (key.ctrl && (input === "w" || input === "W")) {
        // Ctrl+W: Hapus kata sebelum cursor (sama seperti Ctrl+Backspace)
        const beforeCursor = originalValue.slice(0, cursorOffset);
        const afterCursor = originalValue.slice(cursorOffset);
        const trimmed = beforeCursor.trimEnd();
        const lastSpace = trimmed.lastIndexOf(" ");
        if (lastSpace === -1) {
          nextValue = afterCursor;
          nextCursorOffset = 0;
        } else {
          nextValue = trimmed.slice(0, lastSpace + 1) + afterCursor;
          nextCursorOffset = lastSpace + 1;
        }
      } else if (key.ctrl && (input === "k" || input === "K")) {
        // Ctrl+K: Hapus dari cursor sampai akhir
        nextValue = originalValue.slice(0, cursorOffset);
        nextCursorOffset = cursorOffset;
      } else if (key.ctrl && (input === "a" || input === "A")) {
        // Ctrl+A: Ke awal baris
        nextCursorOffset = 0;
      } else if (key.ctrl && (input === "e" || input === "E")) {
        // Ctrl+E: Ke akhir baris
        nextCursorOffset = originalValue.length;
      }
      else if (key.backspace || key.delete) {
        if (cursorOffset > 0) {
          nextValue =
            originalValue.slice(0, cursorOffset - 1) +
            originalValue.slice(cursorOffset, originalValue.length);
          nextCursorOffset--;
        }
      }
      else {
        nextValue =
          originalValue.slice(0, cursorOffset) +
          input +
          originalValue.slice(cursorOffset, originalValue.length);
        nextCursorOffset += input.length;
        if (input.length > 1) {
          nextCursorWidth = input.length;
        }
      }

      // Boundary checks - gunakan cursorOffset (nilai lama), bukan nextCursorOffset
      if (cursorOffset < 0) nextCursorOffset = 0;
      if (cursorOffset > originalValue.length) {
        nextCursorOffset = originalValue.length;
      }

      setState({
        cursorOffset: nextCursorOffset,
        cursorWidth: nextCursorWidth,
      });

      if (nextValue !== originalValue) {
        onChange(nextValue);
      }
    },
    { isActive: focus }
  );

  // Render dengan cursor
  let renderedValue = value;
  let renderedPlaceholder = placeholder ? chalk.grey(placeholder) : undefined;

  if (showCursor && focus) {
    renderedPlaceholder =
      placeholder.length > 0
        ? chalk.inverse(placeholder[0]) + chalk.grey(placeholder.slice(1))
        : chalk.inverse(" ");
    renderedValue = value.length > 0 ? "" : chalk.inverse(" ");
    let i = 0;
    for (const char of value) {
      renderedValue +=
        i >= cursorOffset - cursorActualWidth && i <= cursorOffset
          ? chalk.inverse(char)
          : char;
      i++;
    }
    if (value.length > 0 && cursorOffset === value.length) {
      renderedValue += chalk.inverse(" ");
    }
  }

  return (
    <Text>
      {placeholder
        ? value.length > 0
          ? renderedValue
          : renderedPlaceholder
        : renderedValue}
    </Text>
  );
}
