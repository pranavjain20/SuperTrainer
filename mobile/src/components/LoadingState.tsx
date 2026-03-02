import { ActivityIndicator, View } from "react-native";

import { colors } from "@/src/constants/tokens";

export function LoadingState() {
  return (
    <View className="flex-1 items-center justify-center">
      <ActivityIndicator size="large" color={colors.blue[500]} />
    </View>
  );
}
