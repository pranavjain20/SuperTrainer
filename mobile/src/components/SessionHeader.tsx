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
      {/* Back button */}
      <Pressable
        onPress={onBack}
        className="flex-row items-center mb-3 -ml-1"
        hitSlop={{ top: 16, bottom: 16, left: 12, right: 24 }}
      >
        <FontAwesome name="chevron-left" size={16} color={colors.blue[500]} />
        <ThemedText variant="body-medium" color={colors.blue[500]} style={{ marginLeft: 6 }}>
          Back
        </ThemedText>
      </Pressable>

      {/* Client name */}
      <ThemedText variant="display" style={{ fontSize: 30, letterSpacing: -0.5 }}>{clientName}</ThemedText>

      {/* Status row */}
      <View className="flex-row items-center mt-3" style={{ gap: 10 }}>
        <View
          className="flex-row items-center flex-1 rounded-xl justify-center py-3"
          style={{ backgroundColor: status.color + "20" }}
        >
          <View
            className="w-2.5 h-2.5 rounded-full mr-2.5"
            style={{ backgroundColor: status.color }}
          />
          <ThemedText variant="body-medium" color={status.color} style={{ fontFamily: "Inter-Bold", fontSize: 15 }}>
            {status.label}
          </ThemedText>
        </View>

        {showEndButton && onEndPress && (
          <Pressable
            onPress={onEndPress}
            disabled={isEnding}
            className="flex-1 rounded-xl items-center justify-center py-3"
            style={{
              backgroundColor: colors.red[500],
              opacity: isEnding ? 0.5 : 1,
            }}
          >
            <ThemedText variant="body-medium" color="#FFFFFF" style={{ fontFamily: "Inter-Bold", fontSize: 15 }}>
              End Session
            </ThemedText>
          </Pressable>
        )}
      </View>
    </View>
  );
}
