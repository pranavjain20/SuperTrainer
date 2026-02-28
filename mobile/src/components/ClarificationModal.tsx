/**
 * Custom modal shown when the parser can't understand a voice clip.
 *
 * Replaces the native Alert.alert with a styled modal that matches
 * the app's design language. Three actions:
 *   - "Speak again" — dismiss and let the trainer re-record
 *   - "Type it out" — open the ManualEntryModal
 *   - "Cancel"      — dismiss without action
 */

import { Modal, Pressable, Text, View } from "react-native";

import { colors } from "@/src/constants/colors";

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
        style={{ backgroundColor: "rgba(0, 0, 0, 0.4)" }}
      >
        {/* Card */}
        <View className="bg-white rounded-2xl w-full overflow-hidden">
          {/* Header */}
          <View className="px-6 pt-6 pb-2">
            <Text
              className="text-[11px] font-bold uppercase tracking-widest mb-2"
              style={{ color: colors.textTertiary }}
            >
              Didn't catch that
            </Text>
            <Text className="text-[15px] leading-6 text-gray-700 font-medium">
              {reason}
            </Text>
          </View>

          {/* Actions */}
          <View className="px-5 pt-4 pb-5 gap-2.5">
            {/* Speak again */}
            <Pressable
              onPress={onSpeakAgain}
              className="py-3.5 rounded-xl items-center"
              style={{ backgroundColor: colors.primary }}
            >
              <Text style={{ fontSize: 15, fontWeight: "700", color: "#FFFFFF" }}>
                Speak again
              </Text>
            </Pressable>

            {/* Type it out */}
            <Pressable
              onPress={onTypeIt}
              className="py-3.5 rounded-xl items-center"
              style={{
                backgroundColor: colors.primaryLight,
              }}
            >
              <Text style={{ fontSize: 15, fontWeight: "700", color: colors.primary }}>
                Type it out
              </Text>
            </Pressable>

            {/* Cancel */}
            <Pressable
              onPress={onCancel}
              className="py-3 items-center"
            >
              <Text style={{ fontSize: 14, fontWeight: "600", color: colors.textTertiary }}>
                Cancel
              </Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}
