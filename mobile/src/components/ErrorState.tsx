import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Pressable, Text, View } from "react-native";

import { colors } from "@/src/constants/colors";

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
      <FontAwesome name="exclamation-circle" size={48} color={colors.error} />
      <Text className="text-base text-gray-700 mt-4 text-center">{message}</Text>
      {onRetry && (
        <Pressable
          onPress={onRetry}
          className="mt-4 px-6 py-2.5 rounded-lg active:opacity-80"
          style={{ backgroundColor: colors.primary }}
        >
          <Text className="text-white font-semibold text-sm">Try Again</Text>
        </Pressable>
      )}
    </View>
  );
}
