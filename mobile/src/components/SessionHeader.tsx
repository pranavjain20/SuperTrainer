/**
 * Shared header for the session recording screen.
 *
 * Used in both active (recording) and ended (summary) states.
 * The only difference: active state optionally shows an END SESSION button.
 */

import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

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
    <View
      className="pb-4 px-5"
      style={{ backgroundColor: colors.bg.surface1, paddingTop: insets.top + 8 }}
    >
      <Pressable
        onPress={onBack}
        className="flex-row items-center mb-3 -ml-1"
        hitSlop={{ top: 16, bottom: 16, left: 12, right: 24 }}
      >
        <FontAwesome name="chevron-left" size={20} color={colors.blue[500]} />
        <ThemedText variant="title-3" color={colors.blue[500]} style={{ marginLeft: 8 }}>
          Back
        </ThemedText>
      </Pressable>

      <ThemedText variant="display" style={{ fontSize: 28 }}>{clientName}</ThemedText>

      <View className="flex-row items-end mt-2.5">
        <ThemedText variant="body-medium" color={colors.text.secondary}>{sessionTime}</ThemedText>
        <View
          className="flex-row items-center px-4 py-2 rounded-full ml-3"
          style={{ backgroundColor: status.color + "25" }}
        >
          <View
            className="w-2.5 h-2.5 rounded-full mr-2"
            style={{ backgroundColor: status.color }}
          />
          <ThemedText variant="body-medium" color={status.color} style={{ fontSize: 14 }}>
            {status.label}
          </ThemedText>
        </View>

        {showEndButton && onEndPress && (
          <Pressable
            onPress={onEndPress}
            disabled={isEnding}
            className="ml-auto rounded-xl items-center justify-center px-5 py-3.5"
            style={{
              backgroundColor: colors.red[500],
              opacity: isEnding ? 0.5 : 1,
            }}
          >
            <ThemedText variant="caption" color={colors.text.primary}>
              END SESSION
            </ThemedText>
          </Pressable>
        )}
      </View>
    </View>
  );
}
