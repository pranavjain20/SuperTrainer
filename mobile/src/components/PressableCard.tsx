/**
 * Conditional Pressable wrapper — renders as Pressable with opacity
 * feedback when onPress is provided, plain View otherwise.
 */

import type { ReactNode } from "react";
import { Pressable, View } from "react-native";

interface PressableCardProps {
  onPress?: () => void;
  children: ReactNode;
}

export function PressableCard({ onPress, children }: PressableCardProps) {
  if (onPress) {
    return (
      <Pressable onPress={onPress} style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}>
        {children}
      </Pressable>
    );
  }
  return <View>{children}</View>;
}
