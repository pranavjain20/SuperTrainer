import FontAwesome from "@expo/vector-icons/FontAwesome";
import { ComponentProps } from "react";
import { View } from "react-native";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

interface EmptyStateProps {
  icon: ComponentProps<typeof FontAwesome>["name"];
  title: string;
  subtitle?: string;
}

export function EmptyState({ icon, title, subtitle }: EmptyStateProps) {
  return (
    <View className="flex-1 items-center justify-center px-10">
      <FontAwesome name={icon} size={64} color={colors.text.tertiary} />
      <ThemedText variant="title-2" style={{ marginTop: 20, textAlign: "center" }}>{title}</ThemedText>
      {subtitle && (
        <ThemedText variant="body" color={colors.text.secondary} style={{ marginTop: 8, textAlign: "center" }}>
          {subtitle}
        </ThemedText>
      )}
    </View>
  );
}
