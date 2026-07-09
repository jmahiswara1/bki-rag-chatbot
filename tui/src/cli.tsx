#!/usr/bin/env node
import React from "react";
import { render } from "ink";
import App from "./app.js";

const args = process.argv.slice(2);
let mode = "default";

const modeIdx = args.indexOf("--mode");
if (modeIdx !== -1 && args[modeIdx + 1]) {
  const candidate = args[modeIdx + 1];
  if (candidate === "default" || candidate === "fast") {
    mode = candidate;
  }
}

// Check if stdin supports raw mode (required by Ink)
if (!process.stdin.isTTY) {
  console.error(
    "Error: This terminal does not support interactive mode.\n" +
    "Please run this command in a proper terminal (Windows Terminal, cmd, or PowerShell).\n" +
    "If you're running through an IDE, try opening a terminal window directly."
  );
  process.exit(1);
}

render(<App mode={mode} />, {
  exitOnCtrlC: true,
});
