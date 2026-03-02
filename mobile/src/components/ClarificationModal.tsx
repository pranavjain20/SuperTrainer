/**
 * Custom modal shown when the parser can't understand a voice clip.
 *
 * Replaces the native Alert.alert with a styled modal that matches
 * the app's design language. Three actions:
 *   - "Speak again" — dismiss and let the trainer re-record
 *   - "Type it out" — open the ManualEntryModal
 *   - "Cancel"      — dismiss without action
 */

import { Modal, Pressable, View } from "react-native";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

interface ClarificationModalProps {
  visible: boolean;
  reason: string;
  onSpeakAgain: () => void;
  onTypeIt: () => void;
  onCancel: () => void;
}

export function ClarificationModal({
  visible,
  reason,
  onSpeakAgain,
  onTypeIt,
  onCancel,
}: ClarificationModalProps) {
  return (
    <Modal visible={visible} transparent animationType="fade">
      {/* Backdrop */}
      <View
        className="flex-1 items-center justify-center px-8"
        style={{ backgroundColor: "rgba(0, 0, 0, 0.6)" }}
      >
        {/* Card */}
        <View className="rounded-2xl w-full overflow-hidden" style={{ backgroundColor: colors.bg.surface1 }}>
          {/* Header */}
          <View className="px-6 pt-6 pb-2">
            <ThemedText variant="caption" color={colors.text.tertiary} style={{ marginBottom: 8 }}>
              Didn't catch that
            </ThemedText>
            <ThemedText variant="body" color={colors.text.secondary}>
              {reason}
            </ThemedText>
          </View>

          {/* Actions */}
          <View className="px-5 pt-4 pb-5 gap-2.5">
            {/* Speak again */}
            <Pressable
              onPress={onSpeakAgain}
              className="py-3.5 rounded-xl items-center"
              style={{ backgroundColor: colors.blue[500] }}
            >
              <ThemedText variant="body-medium" color={colors.text.inverse}>
                Speak again
              </ThemedText>
            </Pressable>

            {/* Type it out */}
            <Pressable
              onPress={onTypeIt}
              className="py-3.5 rounded-xl items-center"
              style={{ backgroundColor: colors.blue.alpha12 }}
            >
              <ThemedText variant="body-medium" color={colors.blue[500]}>
                Type it out
              </ThemedText>
            </Pressable>

            {/* Cancel */}
            <Pressable
              onPress={onCancel}
              className="py-3 items-center"
            >
              <ThemedText variant="body-small" color={colors.text.tertiary}>
                Cancel
              </ThemedText>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}
