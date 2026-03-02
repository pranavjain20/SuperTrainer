import FontAwesome from "@expo/vector-icons/FontAwesome";
import { View } from "react-native";

import type { SessionEntry } from "@/src/api/types";
import { PressableCard } from "@/src/components/PressableCard";
import { ThemedText } from "@/src/components/ThemedText";
import { colors, FLAG_BG_COLORS, FLAG_COLORS } from "@/src/constants/tokens";
import { cardBorder } from "@/src/constants/styles";

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
        backgroundColor: FLAG_BG_COLORS[entry.flag_color ?? "green"] ?? FLAG_BG_COLORS.green,
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
        <ThemedText variant="caption" color={flagColor} style={{ flex: 1 }}>
          {heading}
        </ThemedText>
        {onPress && (
          <FontAwesome name="pencil" size={11} color={colors.text.tertiary} style={{ marginLeft: 6, flexShrink: 0 }} />
        )}
      </View>
      <ThemedText variant="body-small" color={colors.text.primary} style={{ lineHeight: 20 }}>
        {entry.observation_text}
      </ThemedText>
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
      <View
        className="mx-4 mb-3 rounded-xl overflow-hidden"
        style={{ backgroundColor: colors.bg.surface1, ...cardBorder }}
      >
        {content}
      </View>
    </PressableCard>
  );
}
