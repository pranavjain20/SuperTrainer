import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Pressable, View } from "react-native";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";
import type { SessionWithClient } from "@/src/hooks/useSessions";
import { formatTime } from "@/src/utils/dates";
import { formatDurationMinutes, getSessionDisplay } from "@/src/utils/sessions";

interface SessionRowProps {
  session: SessionWithClient;
  onPress: (session: SessionWithClient) => void;
  hideClientName?: boolean;
}

export function SessionRow({ session, onPress, hideClientName }: SessionRowProps) {
  const display = getSessionDisplay(session);
  const time = formatTime(session.scheduled_for ?? session.started_at);
  const isCompleted = !!session.ended_at;
  // "In Progress" = started, not ended, and past the scheduled time (or no scheduled time).
  // Future-scheduled sessions get a countdown instead of "Continue Session".
  const isFuture = !!session.scheduled_for &&
    new Date(session.scheduled_for).getTime() > Date.now();
  const isInProgress = !isCompleted && !isFuture;

  return (
    <Pressable
      onPress={() => onPress(session)}
      className="mb-3 mx-4"
      style={{ backgroundColor: colors.bg.surface1, borderRadius: 12, paddingHorizontal: 16, paddingVertical: 14 }}
    >
      {/* Line 1: client name (left) + time (right) — or just time when hideClientName */}
      {!hideClientName ? (
        <View className="flex-row justify-between items-baseline">
          <ThemedText variant="title-3" style={{ flex: 1, marginRight: 12 }} numberOfLines={1}>
            {session.client_name}
          </ThemedText>
          <ThemedText variant="caption" color={colors.text.secondary}>{time}</ThemedText>
        </View>
      ) : (
        <ThemedText variant="caption" color={colors.text.secondary}>{time}</ThemedText>
      )}

      {/* Line 2: status pill + duration (left) + continue button (right) */}
      <View className="flex-row items-center justify-between mt-2">
        <View className="flex-row items-center">
          <View
            className="flex-row items-center px-3.5 py-2 rounded-xl"
            style={{ backgroundColor: display.color + "25" }}
          >
            <View
              className="w-2 h-2 rounded-full mr-2"
              style={{ backgroundColor: display.color }}
            />
            <ThemedText
              variant="caption"
              color={display.color}
            >
              {display.label}
            </ThemedText>
          </View>

          {isCompleted && session.duration_minutes != null && (
            <ThemedText variant="body-small" color={colors.text.tertiary} style={{ marginLeft: 12 }}>
              {formatDurationMinutes(session.duration_minutes!)}
            </ThemedText>
          )}
        </View>

        {isInProgress && (
          <View
            className="flex-row items-center px-3.5 py-2 rounded-xl"
            style={{ backgroundColor: colors.blue[500] }}
          >
            <ThemedText variant="caption" color={colors.text.inverse}>
              Continue Session
            </ThemedText>
            <FontAwesome name="chevron-right" size={9} color={colors.text.inverse} style={{ marginLeft: 6 }} />
          </View>
        )}
      </View>
    </Pressable>
  );
}
