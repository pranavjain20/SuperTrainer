/**
 * Bottom-sheet confirmation dialog — slides up, backdrop tap to cancel.
 * Matches the existing edit modal pattern (ObservationEditModal, etc.).
 */

import { Modal, Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

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
        style={{ backgroundColor: "rgba(0, 0, 0, 0.6)" }}
      />

      {/* Sheet */}
      <View
        className="rounded-t-3xl px-5 pt-6"
        style={{ backgroundColor: colors.bg.surface1, paddingBottom: Math.max(insets.bottom, 20) }}
      >
        <ThemedText variant="title-2">{title}</ThemedText>
        {subtitle && (
          <ThemedText variant="body" color={colors.text.secondary} style={{ marginTop: 4 }}>
            {subtitle}
          </ThemedText>
        )}

        <View className="flex-row gap-3 mt-6">
          <Pressable
            onPress={onCancel}
            className="flex-1 py-3.5 rounded-xl items-center"
            style={{ backgroundColor: colors.bg.surface2 }}
          >
            <ThemedText variant="body-medium" color={colors.text.secondary}>
              Cancel
            </ThemedText>
          </Pressable>
          <Pressable
            onPress={onConfirm}
            className="flex-1 py-3.5 rounded-xl items-center"
            style={{ backgroundColor: destructive ? colors.red[500] : colors.blue[500] }}
          >
            <ThemedText variant="body-medium" color={destructive ? colors.text.primary : colors.text.inverse}>
              {confirmText}
            </ThemedText>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}
