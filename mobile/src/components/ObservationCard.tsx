import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Text, View } from "react-native";

import type { SessionEntry } from "@/src/api/types";
import { PressableCard } from "@/src/components/PressableCard";
import { colors, FLAG_COLORS } from "@/src/constants/colors";
import { cardShadow } from "@/src/constants/styles";

interface ObservationCardProps {
  entry: SessionEntry;
  onPress?: () => void;
  /** When true, renders without its own card wrapper (for use inside a parent container). */
  contained?: boolean;
}

function truncateHeading(text: string, maxWords = 4): string {
  const words = text.split(/\s+/);
  if (words.length <= maxWords) return text;
  return words.slice(0, maxWords).join(" ");
}

export function ObservationCard({ entry, onPress, contained }: ObservationCardProps) {
  const flagColor = FLAG_COLORS[entry.flag_color ?? "green"] ?? FLAG_COLORS.green;
  const heading = truncateHeading(entry.flag_reason ?? "Observation");
  const isWarning = entry.flag_color === "red" || entry.flag_color === "orange";

  const content = (
    <View
      className="px-4 py-3"
      style={{
        backgroundColor: flagColor + "12",
        borderLeftWidth: 4,
        borderLeftColor: flagColor,
      }}
    >
      <View className="flex-row items-center mb-1.5">
        {isWarning && (
          <FontAwesome
            name="exclamation-triangle"
            size={12}
            color={flagColor}
            style={{ marginRight: 6 }}
          />
        )}
        <Text
          style={{ fontSize: 12, fontWeight: "700", color: flagColor, textTransform: "uppercase", letterSpacing: 0.8, flex: 1 }}
        >
          {heading}
        </Text>
        {onPress && (
          <FontAwesome name="pencil" size={11} color={colors.textTertiary} style={{ marginLeft: 6, flexShrink: 0 }} />
        )}
      </View>
      <Text style={{ fontSize: 14, fontWeight: "500", color: colors.text, lineHeight: 20 }}>
        {entry.observation_text}
      </Text>
    </View>
  );

  if (contained) {
    return (
      <PressableCard onPress={onPress}>
        <View style={{ paddingHorizontal: 12, paddingVertical: 8 }}>
          <View style={{ borderRadius: 8, overflow: "hidden" }}>
            {content}
          </View>
        </View>
      </PressableCard>
    );
  }

  return (
    <PressableCard onPress={onPress}>
      <View className="mx-4 mb-3 rounded-xl overflow-hidden" style={cardShadow}>
        {content}
      </View>
    </PressableCard>
  );
}
