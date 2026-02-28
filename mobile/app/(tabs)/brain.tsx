import { Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

export default function BrainScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View className="flex-1 bg-[#FAFAFA]">
      <View className="px-5 pb-4 bg-white" style={{ paddingTop: insets.top + 12 }}>
        <Text className="text-3xl font-bold text-gray-900">Brain</Text>
        <Text className="text-base font-semibold text-gray-600 mt-1">AI Assistant</Text>
      </View>
      <View className="flex-1 items-center justify-center px-8">
        <Text className="text-base text-gray-400 text-center">Coming in Phase 3</Text>
      </View>
    </View>
  );
}
