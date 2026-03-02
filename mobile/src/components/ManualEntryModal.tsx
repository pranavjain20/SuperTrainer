/**
 * Bottom-sheet modal for manually typing a training entry.
 *
 * Opens when the trainer taps "Type it out" on a clarification modal.
 * Always starts blank — the parser couldn't understand the voice clip,
 * so the trainer types what they actually meant. Text goes through the
 * same Claude parser pipeline as voice clips to create proper exercise
 * cards (not just raw observations).
 */

import { useState } from "react";
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  TextInput,
  View,
} from "react-native";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

interface ManualEntryModalProps {
  visible: boolean;
  isSaving: boolean;
  onSave: (text: string) => void;
  onClose: () => void;
}

export function ManualEntryModal({
  visible,
  isSaving,
  onSave,
  onClose,
}: ManualEntryModalProps) {
  const [text, setText] = useState("");
  const canSave = text.trim().length > 0 && !isSaving;

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        className="flex-1 justify-end"
      >
        {/* Backdrop */}
        <Pressable
          className="flex-1"
          onPress={isSaving ? undefined : onClose}
          style={{ backgroundColor: "rgba(0, 0, 0, 0.6)" }}
        />

        {/* Sheet */}
        <View className="rounded-t-3xl" style={{ backgroundColor: colors.bg.surface1 }}>
          {/* Header */}
          <View className="px-5 pt-5 pb-3" style={{ borderBottomWidth: 1, borderBottomColor: colors.border.subtle }}>
            <ThemedText variant="title-2">Type Entry</ThemedText>
            <ThemedText variant="small" color={colors.text.tertiary} style={{ marginTop: 4 }}>
              e.g. "bench press 3 sets of 10 at 80 kilos"
            </ThemedText>
          </View>

          <View className="px-5 pt-4">
            <TextInput
              className="rounded-2xl px-5 py-4"
              style={{
                backgroundColor: colors.bg.surface2,
                fontSize: 16,
                lineHeight: 24,
                fontFamily: "Inter-Regular",
                color: colors.text.primary,
                minHeight: 140,
              }}
              value={text}
              onChangeText={setText}
              placeholder="What happened?"
              placeholderTextColor={colors.text.tertiary}
              multiline
              numberOfLines={5}
              textAlignVertical="top"
              autoFocus
            />
          </View>

          {/* Footer */}
          <View className="px-5 pt-4 pb-8 mt-4" style={{ borderTopWidth: 1, borderTopColor: colors.border.subtle }}>
            <View className="flex-row justify-end gap-3">
              <Pressable
                onPress={onClose}
                disabled={isSaving}
                className="px-6 py-3 rounded-xl"
                style={{ backgroundColor: colors.bg.surface2 }}
              >
                <ThemedText variant="body-medium" color={colors.text.secondary}>
                  Cancel
                </ThemedText>
              </Pressable>
              <Pressable
                onPress={() => onSave(text.trim())}
                disabled={!canSave}
                className="px-6 py-3 rounded-xl"
                style={{
                  backgroundColor: colors.blue[500],
                  opacity: canSave ? 1 : 0.5,
                }}
              >
                <ThemedText variant="body-medium" color={colors.text.inverse}>
                  {isSaving ? "Saving..." : "Save"}
                </ThemedText>
              </Pressable>
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
