import { ActivityIndicator, View } from "react-native";

import { colors } from "@/src/constants/colors";

export function LoadingState() {
  return (
    <View className="flex-1 items-center justify-center">
      <ActivityIndicator size="large" color={colors.primary} />
    </View>
  );
}
