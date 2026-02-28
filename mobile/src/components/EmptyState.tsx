import FontAwesome from "@expo/vector-icons/FontAwesome";
import { ComponentProps } from "react";
import { Text, View } from "react-native";

import { colors } from "@/src/constants/colors";

interface EmptyStateProps {
  icon: ComponentProps<typeof FontAwesome>["name"];
  title: string;
  subtitle?: string;
}

export function EmptyState({ icon, title, subtitle }: EmptyStateProps) {
  return (
    <View className="flex-1 items-center justify-center px-10">
      <FontAwesome name={icon} size={64} color={colors.textTertiary} />
      <Text className="text-2xl font-bold text-gray-900 mt-5 text-center">{title}</Text>
      {subtitle && (
        <Text className="text-base text-gray-500 mt-2 text-center">{subtitle}</Text>
      )}
    </View>
  );
}
