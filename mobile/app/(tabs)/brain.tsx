import { View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

export default function BrainScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View className="flex-1 bg-base">
      <View
        className="px-5 pb-4 bg-surface-1 border-b border-border-subtle"
        style={{ paddingTop: insets.top + 12 }}
      >
        <ThemedText variant="display">Brain</ThemedText>
        <ThemedText variant="body-medium" color={colors.text.secondary} style={{ marginTop: 4 }}>
          AI Assistant
        </ThemedText>
      </View>
      <View className="flex-1 items-center justify-center px-8">
        <ThemedText variant="body" color={colors.text.tertiary} style={{ textAlign: "center" }}>
          Coming in Phase 3
        </ThemedText>
      </View>
    </View>
  );
}
