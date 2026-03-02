import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Pressable, View } from "react-native";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  message = "Something went wrong",
  onRetry,
}: ErrorStateProps) {
  return (
    <View className="flex-1 items-center justify-center px-8">
      <FontAwesome name="exclamation-circle" size={48} color={colors.red[500]} />
      <ThemedText variant="body" color={colors.text.secondary} style={{ marginTop: 16, textAlign: "center" }}>
        {message}
      </ThemedText>
      {onRetry && (
        <Pressable
          onPress={onRetry}
          className="mt-4 px-6 py-2.5 rounded-lg active:opacity-80"
          style={{ backgroundColor: colors.blue[500] }}
        >
          <ThemedText variant="body-medium" color={colors.text.inverse} style={{ fontSize: 14 }}>
            Try Again
          </ThemedText>
        </Pressable>
      )}
    </View>
  );
}
