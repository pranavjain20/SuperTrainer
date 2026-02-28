/**
 * Post-session summary card — compact "session is done" view.
 *
 * Green success banner → workout type → stat pills.
 * Intentionally minimal — plan input lives in its own card below.
 */

import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Text, View } from "react-native";

import { colors } from "@/src/constants/colors";
import { cardShadow } from "@/src/constants/styles";

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
      className="mx-4 mt-4 rounded-2xl bg-white overflow-hidden"
      style={cardShadow}
    >
      {/* ── Green success banner ── */}
      <View style={{ backgroundColor: colors.success + "14", paddingHorizontal: 20, paddingTop: 16, paddingBottom: 14 }}>
        <View className="flex-row items-center justify-between">
          <View className="flex-row items-center">
            <View
              className="w-9 h-9 rounded-full items-center justify-center mr-3"
              style={{ backgroundColor: colors.success + "2A" }}
            >
              <FontAwesome name="check" size={16} color={colors.success} />
            </View>
            <Text style={{ fontSize: 18, fontWeight: "800", color: colors.success, letterSpacing: 0.3 }}>
              Session Complete
            </Text>
          </View>

          <View
            className="px-3.5 py-1.5 rounded-full"
            style={{ backgroundColor: colors.success + "22" }}
          >
            <Text style={{ fontSize: 15, fontWeight: "800", color: colors.success }}>
              {duration}
            </Text>
          </View>
        </View>
      </View>

      {/* ── Workout type + stats ── */}
      <View className="px-5 pt-3 pb-3.5">
        {exerciseCount > 0 || isClassifying ? (
          <>
            <Text style={{ fontSize: 17, fontWeight: "700", color: colors.text }}>
              {isClassifying ? "Analyzing..." : (workoutType ?? "Session")}
            </Text>
            {statsLine.length > 0 && (
              <Text style={{ fontSize: 14, fontWeight: "600", color: colors.textSecondary, marginTop: 3 }}>
                {statsLine}
              </Text>
            )}
          </>
        ) : (
          <Text style={{ fontSize: 14, fontWeight: "600", color: colors.text }}>
            No exercises recorded
          </Text>
        )}
      </View>
    </View>
  );
}
