import React, { useState, useEffect } from "react";
import { Text } from "ink";

const FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"];
const INTERVAL = 80;

interface SpinnerProps {
  color?: string;
}

export default function Spinner({ color = "cyan" }: SpinnerProps) {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setFrame((prev) => (prev + 1) % FRAMES.length);
    }, INTERVAL);
    return () => clearInterval(timer);
  }, []);

  return (
    <Text color={color} bold>
      {FRAMES[frame]}
    </Text>
  );
}
