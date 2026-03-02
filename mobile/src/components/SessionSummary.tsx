/**
 * Post-session summary card — compact "session is done" view.
 *
 * Green success banner → workout type → stat pills.
 * Intentionally minimal — plan input lives in its own card below.
 */

import FontAwesome from "@expo/vector-icons/FontAwesome";
import { View } from "react-native";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";
import { cardBorder } from "@/src/constants/styles";

interface SessionSummaryProps {
  duration: string;
  exerciseCount: number;
  totalSets: number;
  workoutType: string | null;
  isClassifying: boolean;
}

export function SessionSummary({
  duration,
  exerciseCount,
  totalSets,
  workoutType,
  isClassifying,
}: SessionSummaryProps) {
  const statsLine = [
    exerciseCount > 0 && `${exerciseCount} ${exerciseCount === 1 ? "exercise" : "exercises"}`,
    totalSets > 0 && `${totalSets} ${totalSets === 1 ? "set" : "sets"}`,
  ]
    .filter(Boolean)
    .join("  ·  ");

  return (
    <View
      className="mx-4 mt-4 rounded-xl overflow-hidden"
      style={{ backgroundColor: colors.bg.surface1, ...cardBorder }}
    >
      {/* ── Green success banner ── */}
      <View style={{ backgroundColor: colors.green.alpha12, paddingHorizontal: 20, paddingTop: 16, paddingBottom: 14 }}>
        <View className="flex-row items-center justify-between">
          <View className="flex-row items-center">
            <View
              className="w-9 h-9 rounded-full items-center justify-center mr-3"
              style={{ backgroundColor: colors.green.alpha12 }}
            >
              <FontAwesome name="check" size={16} color={colors.green[500]} />
            </View>
            <ThemedText variant="title-2" color={colors.green[500]}>
              Session Complete
            </ThemedText>
          </View>

          <View
            className="px-3.5 py-1.5 rounded-full"
            style={{ backgroundColor: colors.green.alpha12 }}
          >
            <ThemedText variant="data-bold" color={colors.green[500]}>
              {duration}
            </ThemedText>
          </View>
        </View>
      </View>

      {/* ── Workout type + stats ── */}
      <View className="px-5 pt-3 pb-3.5">
        {exerciseCount > 0 || isClassifying ? (
          <>
            <ThemedText variant="title-3">
              {isClassifying ? "Analyzing..." : (workoutType ?? "Session")}
            </ThemedText>
            {statsLine.length > 0 && (
              <ThemedText variant="body-small" color={colors.text.secondary} style={{ marginTop: 3 }}>
                {statsLine}
              </ThemedText>
            )}
          </>
        ) : (
          <ThemedText variant="body-small">
            No exercises recorded
          </ThemedText>
        )}
      </View>
    </View>
  );
}
