import FontAwesome from "@expo/vector-icons/FontAwesome";
import { View } from "react-native";

import type { SessionEntry, SetData } from "@/src/api/types";
import { PressableCard } from "@/src/components/PressableCard";
import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";
import { cardBorder } from "@/src/constants/styles";
import { getSetNumber, getSetReps, getSetWeight } from "@/src/utils/sets";
import { capitalizeFirst, capitalizeWords } from "@/src/utils/strings";

interface ExerciseCardProps {
  entry: SessionEntry;
  exerciseNumber?: number;
  onPress?: () => void;
  /** When true, renders without its own card wrapper (for use inside a parent container). */
  contained?: boolean;
}

const COL = { set: 32, reps: 44, weight: 64, rpe: 40 };

export function ExerciseCard({ entry, exerciseNumber, onPress, contained }: ExerciseCardProps) {
  const sets = entry.sets ?? [];
  const name = capitalizeWords(
    entry.exercise_name ?? entry.exercise_canonical ?? "Unknown",
  );

  const content = (
    <>
      {/* Exercise name header */}
      <View className="flex-row items-center px-4 pt-3.5 pb-2.5">
        {exerciseNumber != null && (
          <View
            className="items-center justify-center mr-2.5"
            style={{
              width: 28,
              height: 28,
              borderRadius: 14,
              backgroundColor: colors.blue[500],
            }}
          >
            <ThemedText variant="caption" color={colors.text.inverse} style={{ fontSize: 13, letterSpacing: 0 }}>
              {exerciseNumber}
            </ThemedText>
          </View>
        )}
        <ThemedText variant="title-2" style={{ flex: 1 }}>
          {name}
        </ThemedText>
        {onPress && (
          <FontAwesome name="pencil" size={13} color={colors.text.tertiary} style={{ marginLeft: 8 }} />
        )}
      </View>

      {/* Set table */}
      {sets.length > 0 && (
        <View>
          {/* Header */}
          <View
            className="flex-row px-4 py-2"
            style={{ backgroundColor: colors.blue.alpha12 }}
          >
            <ThemedText variant="caption" color={colors.text.secondary} style={{ width: COL.set }}>Set</ThemedText>
            <ThemedText variant="caption" color={colors.text.secondary} style={{ width: COL.reps }}>Reps</ThemedText>
            <ThemedText variant="caption" color={colors.text.secondary} style={{ width: COL.weight }}>Weight</ThemedText>
            <ThemedText variant="caption" color={colors.text.secondary} style={{ width: COL.rpe }}>RPE</ThemedText>
            <ThemedText variant="caption" color={colors.text.secondary} style={{ flex: 1 }}>Notes</ThemedText>
          </View>

          {/* Rows */}
          {sets.map((set: SetData, i: number) => {
            const hasNote = !!set.notes;
            return (
              <View
                key={getSetNumber(set, i)}
                className="flex-row items-center px-4 py-2.5"
                style={{
                  borderTopWidth: 1,
                  borderTopColor: colors.border.subtle,
                }}
              >
                <ThemedText variant="data" color={colors.text.secondary} style={{ width: COL.set, fontSize: 13 }}>{getSetNumber(set, i)}</ThemedText>
                <ThemedText variant="data" style={{ width: COL.reps }}>{getSetReps(set)}</ThemedText>
                <ThemedText variant="data" style={{ width: COL.weight }}>{getSetWeight(set)}</ThemedText>
                <ThemedText variant="data" style={{ width: COL.rpe }}>{set.rpe ?? "—"}</ThemedText>
                <ThemedText
                  variant="body-small"
                  color={hasNote ? colors.text.primary : colors.text.tertiary}
                  style={{ flex: 1 }}
                  numberOfLines={2}
                >
                  {set.notes ? capitalizeFirst(set.notes) : "—"}
                </ThemedText>
              </View>
            );
          })}
        </View>
      )}
    </>
  );

  if (contained) {
    return <PressableCard onPress={onPress}>{content}</PressableCard>;
  }

  return (
    <PressableCard onPress={onPress}>
      <View
        className="mx-4 mb-3 rounded-xl overflow-hidden"
        style={{ backgroundColor: colors.bg.surface1, ...cardBorder }}
      >
        {content}
      </View>
    </PressableCard>
  );
}
