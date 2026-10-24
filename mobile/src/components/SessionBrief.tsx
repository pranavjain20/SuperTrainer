/**
 * "AI notes" on an upcoming session: a bar the trainer taps to see Claude's
 * brief on that client (recent pain, lifts that moved, muscle groups missed).
 * The brief is only fetched once the bar is opened.
 */

import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ActivityIndicator, Pressable, View } from "react-native";

import { getSessionBrief } from "@/src/api/sessions";
import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

export const briefQueryKey = (sessionId: string) => ["brief", sessionId] as const;

/** Claude writes one note per "- " line; anything else is shown as its own line. */
export function briefNotes(brief: string): string[] {
  return brief
    .split("\n")
    .map((line) => line.replace(/^\s*-\s*/, "").trim())
    .filter(Boolean);
}

export function SessionBrief({ sessionId }: { sessionId: string }) {
  const [open, setOpen] = useState(false);
  const brief = useQuery({
    queryKey: briefQueryKey(sessionId),
    queryFn: () => getSessionBrief(sessionId),
    enabled: open,
    // Each try is a Claude call; the trainer can tap to retry instead
    retry: false,
    staleTime: 30 * 60_000,
  });

  return (
    <View
      className="mt-3 rounded-lg"
      style={{
        backgroundColor: colors.ai.alpha10,
        borderLeftWidth: 3,
        borderLeftColor: colors.ai[500],
      }}
    >
      <Pressable
        onPress={() => setOpen((o) => !o)}
        className="flex-row items-center px-3 py-2.5"
        accessibilityRole="button"
        accessibilityLabel={open ? "Hide AI notes" : "Show AI notes"}
      >
        <FontAwesome name="bolt" size={12} color={colors.ai[400]} />
        <ThemedText
          variant="caption"
          color={colors.ai[400]}
          style={{ marginLeft: 6, flex: 1 }}
        >
          AI notes
        </ThemedText>
        <FontAwesome
          name={open ? "chevron-up" : "chevron-down"}
          size={10}
          color={colors.ai[400]}
        />
      </Pressable>

      {open && (
        <View className="px-3 pb-3">
          {brief.isPending ? (
            <View className="flex-row items-center">
              <ActivityIndicator size="small" color={colors.ai[400]} />
              <ThemedText
                variant="body-small"
                color={colors.text.secondary}
                style={{ marginLeft: 8 }}
              >
                Reading this client's history…
              </ThemedText>
            </View>
          ) : brief.isError ? (
            <Pressable onPress={() => brief.refetch()}>
              <ThemedText variant="body-small" color={colors.text.secondary}>
                Couldn't load the notes. Tap to try again.
              </ThemedText>
            </Pressable>
          ) : brief.data ? (
            briefNotes(brief.data).map((note, i) => (
              <View key={i} className="flex-row" style={{ marginTop: i ? 8 : 0 }}>
                <ThemedText variant="body" color={colors.ai[400]} style={{ width: 14 }}>
                  •
                </ThemedText>
                <ThemedText
                  variant="body"
                  color={colors.text.primary}
                  style={{ flex: 1, lineHeight: 21 }}
                >
                  {note}
                </ThemedText>
              </View>
            ))
          ) : (
            <ThemedText variant="body-small" color={colors.text.secondary}>
              No sessions with this client in the last four weeks yet.
            </ThemedText>
          )}
        </View>
      )}
    </View>
  );
}
