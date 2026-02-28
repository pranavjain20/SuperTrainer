import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Animated, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "@/src/constants/colors";
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
        backgroundColor: colors.primary,
        borderRadius: 14,
        flexDirection: "row",
        alignItems: "center",
        paddingHorizontal: 16,
        zIndex: 100,
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.2,
        shadowRadius: 8,
        elevation: 8,
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
              backgroundColor: colors.success,
              opacity: pulseAnim.interpolate({ inputRange: [0.3, 1], outputRange: [0, 0.25] }),
            }}
          />
          {/* Solid dot */}
          <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: colors.success }} />
        </View>
        <Text
          style={{ color: "#FFFFFF", fontWeight: "700", fontSize: 15 }}
          numberOfLines={1}
        >
          {activeClientName}
        </Text>
      </View>

      {/* Timer + chevron */}
      <Text style={{ color: "rgba(255,255,255,0.85)", fontSize: 14, fontWeight: "600", marginRight: 8 }}>
        {elapsed}
      </Text>
      <FontAwesome name="chevron-right" size={12} color="rgba(255,255,255,0.7)" />
    </Pressable>
  );
}
