import { Link, Stack } from "expo-router";
import { View } from "react-native";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

export default function NotFoundScreen() {
  return (
    <>
      <Stack.Screen options={{ title: "Oops!" }} />
      <View className="flex-1 items-center justify-center p-5 bg-base">
        <ThemedText variant="title-2">This screen doesn't exist.</ThemedText>
        <Link href="/" className="mt-4 py-4">
          <ThemedText variant="body-small" color={colors.blue[500]}>
            Go to home screen
          </ThemedText>
        </Link>
      </View>
    </>
  );
}
