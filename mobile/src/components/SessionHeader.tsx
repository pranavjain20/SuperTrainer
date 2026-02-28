/**
 * Shared header for the session recording screen.
 *
 * Used in both active (recording) and ended (summary) states.
 * The only difference: active state optionally shows an END SESSION button.
 */

import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "@/src/constants/colors";

interface StatusDisplay {
  label: string;
  color: string;
}

interface SessionHeaderProps {
  clientName: string;
  sessionTime: string;
  status: StatusDisplay;
  onBack: () => void;
  showEndButton?: boolean;
  isEnding?: boolean;
  onEndPress?: () => void;
}

export function SessionHeader({
  clientName,
  sessionTime,
  status,
  onBack,
  showEndButton,
  isEnding,
  onEndPress,
}: SessionHeaderProps) {
  const insets = useSafeAreaInsets();

  return (
    <View className="bg-white pb-4 px-5" style={{ paddingTop: insets.top + 8 }}>
      <Pressable
        onPress={onBack}
        className="flex-row items-center mb-3 -ml-1"
        hitSlop={{ top: 16, bottom: 16, left: 12, right: 24 }}
      >
        <FontAwesome name="chevron-left" size={20} color={colors.primary} />
        <Text
          className="text-xl font-bold ml-2"
          style={{ color: colors.primary }}
        >
          Back
        </Text>
      </Pressable>

      <Text className="text-3xl font-bold text-gray-900">{clientName}</Text>

      <View className="flex-row items-end mt-2.5">
        <Text className="text-lg font-semibold text-gray-700">{sessionTime}</Text>
        <View
          className="flex-row items-center px-4 py-2 rounded-full ml-3"
          style={{ backgroundColor: status.color + "1A" }}
        >
          <View
            className="w-2.5 h-2.5 rounded-full mr-2"
            style={{ backgroundColor: status.color }}
          />
          <Text className="text-base font-bold" style={{ color: status.color }}>
            {status.label}
          </Text>
        </View>

        {showEndButton && onEndPress && (
          <Pressable
            onPress={onEndPress}
            disabled={isEnding}
            className="ml-auto rounded-xl items-center justify-center px-5 py-3.5"
            style={{
              backgroundColor: colors.error,
              opacity: isEnding ? 0.5 : 1,
            }}
          >
            <Text
              className="font-black tracking-widest text-white"
              style={{ fontSize: 13 }}
            >
              END SESSION
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}
