import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Pressable, Text, View } from "react-native";

import { colors } from "@/src/constants/colors";
import { cardShadow } from "@/src/constants/styles";
import type { SessionWithClient } from "@/src/hooks/useSessions";
import { formatTime } from "@/src/utils/dates";
import { getSessionDisplay } from "@/src/utils/sessions";

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
      className="bg-white rounded-2xl px-5 py-5 mb-3.5 mx-4"
      style={cardShadow}
    >
      {/* Time */}
      <Text className="text-sm font-bold text-gray-900 tracking-wide">{time}</Text>

      {/* Client name */}
      {!hideClientName && (
        <Text className="text-xl font-bold text-gray-900 mt-1.5">
          {session.client_name}
        </Text>
      )}

      {/* Bottom row: status pill (left) + continue/duration (right) */}
      <View className="flex-row items-center justify-between mt-3.5">
        <View className="flex-row items-center">
          <View
            className="flex-row items-center px-3.5 py-2 rounded-xl"
            style={{ backgroundColor: display.color + "18" }}
          >
            <View
              className="w-2 h-2 rounded-full mr-2"
              style={{ backgroundColor: display.color }}
            />
            <Text
              style={{
                fontSize: 11,
                fontWeight: "800",
                letterSpacing: 0.8,
                color: display.color,
                textTransform: "uppercase",
              }}
            >
              {display.label}
            </Text>
          </View>

          {isCompleted && session.duration_minutes != null && (
            <Text className="text-sm font-medium text-gray-400 ml-3">
              {session.duration_minutes} min
            </Text>
          )}
        </View>

        {isInProgress && (
          <View
            className="flex-row items-center px-3.5 py-2 rounded-xl"
            style={{ backgroundColor: colors.primary }}
          >
            <Text
              style={{
                fontSize: 11,
                fontWeight: "800",
                letterSpacing: 0.8,
                color: "#FFFFFF",
                textTransform: "uppercase",
              }}
            >
              Continue Session
            </Text>
            <FontAwesome name="chevron-right" size={9} color="#FFFFFF" style={{ marginLeft: 6 }} />
          </View>
        )}
      </View>
    </Pressable>
  );
}
