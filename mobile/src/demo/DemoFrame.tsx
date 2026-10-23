/**
 * The web demo's page around the app.
 *
 * On a wide screen the app loads inside a phone-sized iframe, so every screen,
 * sheet and modal lays out exactly as it does on a phone. Inside the iframe,
 * or on a narrow screen (a visitor on their phone), the app renders directly.
 */

import { useState, type ReactNode } from "react";
import { Linking, Pressable, ScrollView, useWindowDimensions, View } from "react-native";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

import { resetDemo } from "./store";

const PHONE_WIDTH = 390;
const PHONE_HEIGHT = 844;
const BEZEL = 10;
const WIDE_SCREEN_MIN = 760;
const REPO_URL = "https://github.com/pranavjain20/SuperTrainer";

const TRY_IT = [
  [
    "Log a session by voice",
    "Open a client, start a session and tap the mic. A sample clip plays; tap stop and it turns into an exercise card.",
  ],
  ["Get an AI summary", "End the session and Claude sums up how it went."],
  ["Ask the Brain", "Ask about any client, like how Jake's bench press is going."],
] as const;

export function DemoFrame({ children }: { children: ReactNode }) {
  const { width, height } = useWindowDimensions();
  const [embedded] = useState(() => window.self !== window.top);
  const [frameKey, setFrameKey] = useState(0);

  if (embedded || width < WIDE_SCREEN_MIN) return <>{children}</>;

  // Shrink the phone on short windows rather than cropping it
  const scale = Math.min(1, (height - 48) / (PHONE_HEIGHT + 2 * BEZEL));
  const src = `${window.location.pathname}${window.location.search}`;

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.bg.base }}
      contentContainerStyle={{
        flexGrow: 1,
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        gap: 72,
        padding: 24,
      }}
    >
      <View style={{ maxWidth: 360 }}>
        <ThemedText variant="display" style={{ fontSize: 40, lineHeight: 46 }}>
          SuperTrainer
        </ThemedText>
        <ThemedText
          variant="body"
          color={colors.text.primary}
          style={{ marginTop: 14, fontSize: 18, lineHeight: 27 }}
        >
          Most personal trainers still log sessions in a notebook. With SuperTrainer they
          just say what their client did, and it becomes a clean workout log.
        </ThemedText>
        {TRY_IT.map(([title, detail], i) => (
          <View key={title} style={{ marginTop: i === 0 ? 26 : 14 }}>
            <ThemedText variant="body-medium" color={colors.text.primary}>
              {title}
            </ThemedText>
            <ThemedText
              variant="body"
              color={colors.text.secondary}
              style={{ marginTop: 2, lineHeight: 22 }}
            >
              {detail}
            </ThemedText>
          </View>
        ))}
        <ThemedText
          variant="body-small"
          color={colors.text.tertiary}
          style={{ marginTop: 22, lineHeight: 20 }}
        >
          This demo runs in your browser. Every clip, summary and answer here was produced
          once by the real pipeline (Deepgram for speech, Claude for the rest) and is
          replayed at the speed it ran. What you change stays in this browser.
        </ThemedText>

        <View style={{ flexDirection: "row", gap: 12, marginTop: 28 }}>
          <Pressable
            onPress={() => Linking.openURL(REPO_URL)}
            style={{
              paddingVertical: 12,
              paddingHorizontal: 18,
              borderRadius: 12,
              backgroundColor: colors.blue[500],
            }}
          >
            <ThemedText variant="body-medium" color={colors.text.inverse}>
              Code on GitHub
            </ThemedText>
          </Pressable>
          <Pressable
            onPress={() => {
              resetDemo();
              setFrameKey((k) => k + 1);
            }}
            style={{
              paddingVertical: 12,
              paddingHorizontal: 18,
              borderRadius: 12,
              borderWidth: 1.5,
              borderColor: colors.border.default,
            }}
          >
            <ThemedText variant="body-medium" color={colors.text.primary}>
              Reset demo
            </ThemedText>
          </Pressable>
        </View>
      </View>

      <View
        style={{
          width: (PHONE_WIDTH + 2 * BEZEL) * scale,
          height: (PHONE_HEIGHT + 2 * BEZEL) * scale,
        }}
      >
        <View
          style={{
            width: PHONE_WIDTH + 2 * BEZEL,
            height: PHONE_HEIGHT + 2 * BEZEL,
            padding: BEZEL,
            borderRadius: 56,
            backgroundColor: colors.bg.surface1,
            borderWidth: 1,
            borderColor: colors.border.subtle,
            transform: [{ scale }],
            transformOrigin: "top left",
          }}
        >
          <iframe
            key={frameKey}
            src={frameKey ? "/" : src}
            title="SuperTrainer app"
            allow="autoplay"
            style={{
              width: PHONE_WIDTH,
              height: PHONE_HEIGHT,
              border: 0,
              borderRadius: 46,
              display: "block",
            }}
          />
        </View>
      </View>
    </ScrollView>
  );
}
