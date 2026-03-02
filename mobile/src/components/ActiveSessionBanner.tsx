import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Animated, Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";
import { useRecordingStore } from "@/src/stores/recordingStore";

const TAB_BAR_HEIGHT = 49;

function formatElapsed(startIso: string): string {
  const diff = Math.max(0, Math.floor((Date.now() - new Date(startIso).getTime()) / 1000));
  const mins = Math.floor(diff / 60);
  const secs = diff % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export function ActiveSessionBanner() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const activeSessionId = useRecordingStore((s) => s.activeSessionId);
  const activeClientName = useRecordingStore((s) => s.activeClientName);
  const activeSessionStartedAt = useRecordingStore((s) => s.activeSessionStartedAt);

  const [elapsed, setElapsed] = useState("00:00");

  // Pulsing dot animation
  const pulseAnim = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (!activeSessionId) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.3, duration: 800, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [activeSessionId, pulseAnim]);

  // Elapsed timer
  useEffect(() => {
    if (!activeSessionStartedAt) return;
    setElapsed(formatElapsed(activeSessionStartedAt));
    const interval = setInterval(() => {
      setElapsed(formatElapsed(activeSessionStartedAt));
    }, 1000);
    return () => clearInterval(interval);
  }, [activeSessionStartedAt]);

  if (!activeSessionId) return null;

  return (
    <Pressable
      onPress={() => router.push(`/recording/${activeSessionId}` as any)}
      style={{
        position: "absolute",
        bottom: TAB_BAR_HEIGHT + insets.bottom + 6,
        left: 12,
        right: 12,
        height: 48,
        backgroundColor: colors.blue[500],
        borderRadius: 14,
        flexDirection: "row",
        alignItems: "center",
        paddingHorizontal: 20,
        paddingVertical: 14,
        zIndex: 100,
      }}
    >
      {/* Pulsing dot + client name */}
      <View style={{ flexDirection: "row", alignItems: "center", flex: 1 }}>
        <View style={{ width: 20, height: 20, alignItems: "center", justifyContent: "center", marginRight: 8 }}>
          {/* Glow ring */}
          <Animated.View
            style={{
              position: "absolute",
              width: 18,
              height: 18,
              borderRadius: 9,
              backgroundColor: colors.green[500],
              opacity: pulseAnim.interpolate({ inputRange: [0.3, 1], outputRange: [0, 0.25] }),
            }}
          />
          {/* Solid dot */}
          <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: colors.green[500] }} />
        </View>
        <ThemedText variant="title-3" color={colors.text.inverse} numberOfLines={1}>
          {activeClientName}
        </ThemedText>
      </View>

      {/* Timer + chevron — JetBrains Mono for the timer */}
      <ThemedText variant="data" color={colors.text.inverse} style={{ marginRight: 8, opacity: 0.9 }}>
        {elapsed}
      </ThemedText>
      <FontAwesome name="chevron-right" size={12} color={colors.text.inverse} style={{ opacity: 0.7 }} />
    </Pressable>
  );
}
