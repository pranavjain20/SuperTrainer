/**
 * Bottom-sheet confirmation dialog — slides up, backdrop tap to cancel.
 * Matches the existing edit modal pattern (ObservationEditModal, etc.).
 */

import { Modal, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "@/src/constants/colors";

interface ConfirmSheetProps {
  visible: boolean;
  title: string;
  subtitle?: string;
  confirmText: string;
  onConfirm: () => void;
  onCancel: () => void;
  destructive?: boolean;
}

export function ConfirmSheet({
  visible,
  title,
  subtitle,
  confirmText,
  onConfirm,
  onCancel,
  destructive,
}: ConfirmSheetProps) {
  const insets = useSafeAreaInsets();

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onCancel}>
      {/* Backdrop */}
      <Pressable
        className="flex-1"
        onPress={onCancel}
        style={{ backgroundColor: "rgba(0,0,0,0.3)" }}
      />

      {/* Sheet */}
      <View
        className="bg-white rounded-t-3xl px-5 pt-6"
        style={{ paddingBottom: Math.max(insets.bottom, 20) }}
      >
        <Text className="text-xl font-bold text-gray-900">{title}</Text>
        {subtitle && (
          <Text className="text-base text-gray-500 font-medium mt-1">
            {subtitle}
          </Text>
        )}

        <View className="flex-row gap-3 mt-6">
          <Pressable
            onPress={onCancel}
            className="flex-1 py-3.5 rounded-xl bg-gray-100 items-center"
          >
            <Text
              style={{ fontSize: 15, fontWeight: "700", color: colors.textSecondary }}
            >
              Cancel
            </Text>
          </Pressable>
          <Pressable
            onPress={onConfirm}
            className="flex-1 py-3.5 rounded-xl items-center"
            style={{ backgroundColor: destructive ? colors.error : colors.primary }}
          >
            <Text style={{ fontSize: 15, fontWeight: "700", color: "#FFFFFF" }}>
              {confirmText}
            </Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}
