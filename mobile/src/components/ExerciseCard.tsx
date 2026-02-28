import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Text, View } from "react-native";

import type { SessionEntry, SetData } from "@/src/api/types";
import { PressableCard } from "@/src/components/PressableCard";
import { colors } from "@/src/constants/colors";
import { cardShadow } from "@/src/constants/styles";
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

const headerStyle = {
  fontSize: 11,
  fontWeight: "700" as const,
  color: colors.primary,
  textTransform: "uppercase" as const,
  letterSpacing: 0.8,
};

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
              backgroundColor: colors.primary,
            }}
          >
            <Text style={{ fontSize: 13, fontWeight: "700", color: "#FFFFFF" }}>
              {exerciseNumber}
            </Text>
          </View>
        )}
        <Text className="flex-1" style={{ fontSize: 15, fontWeight: "600", color: colors.text }}>
          {name}
        </Text>
        {onPress && (
          <FontAwesome name="pencil" size={13} color={colors.textTertiary} style={{ marginLeft: 8 }} />
        )}
      </View>

      {/* Set table */}
      {sets.length > 0 && (
        <View>
          {/* Header */}
          <View
            className="flex-row px-4 py-2"
            style={{ backgroundColor: colors.primary + "08" }}
          >
            <Text style={{ ...headerStyle, width: COL.set }}>Set</Text>
            <Text style={{ ...headerStyle, width: COL.reps }}>Reps</Text>
            <Text style={{ ...headerStyle, width: COL.weight }}>Weight</Text>
            <Text style={{ ...headerStyle, width: COL.rpe }}>RPE</Text>
            <Text style={{ ...headerStyle, flex: 1 }}>Notes</Text>
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
                  borderTopColor: colors.borderLight,
                  backgroundColor: undefined,
                }}
              >
                <Text style={{ fontSize: 13, fontWeight: "600", color: colors.textTertiary, width: COL.set }}>{getSetNumber(set, i)}</Text>
                <Text style={{ fontSize: 14, fontWeight: "600", color: colors.text, width: COL.reps }}>{getSetReps(set)}</Text>
                <Text style={{ fontSize: 14, fontWeight: "600", color: colors.text, width: COL.weight }}>{getSetWeight(set)}</Text>
                <Text style={{ fontSize: 14, fontWeight: "600", color: colors.text, width: COL.rpe }}>{set.rpe ?? "—"}</Text>
                <Text
                  style={{
                    fontSize: 13,
                    fontWeight: hasNote ? "600" : "400",
                    color: hasNote ? colors.text : colors.textTertiary,
                    flex: 1,
                  }}
                  numberOfLines={2}
                >
                  {set.notes ? capitalizeFirst(set.notes) : "—"}
                </Text>
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
      <View className="mx-4 mb-3 rounded-xl bg-white overflow-hidden" style={cardShadow}>
        {content}
      </View>
    </PressableCard>
  );
}
