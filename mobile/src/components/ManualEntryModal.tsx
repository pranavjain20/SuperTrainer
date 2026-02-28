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
  Text,
  TextInput,
  View,
} from "react-native";

import { colors } from "@/src/constants/colors";

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
        <Pressable className="flex-1" onPress={isSaving ? undefined : onClose} />

        {/* Sheet */}
        <View className="bg-white rounded-t-3xl">
          {/* Header */}
          <View className="px-5 pt-5 pb-3 border-b border-gray-100">
            <Text className="text-lg font-bold text-gray-900">Type Entry</Text>
            <Text className="text-[13px] mt-1" style={{ color: colors.textTertiary }}>
              e.g. "bench press 3 sets of 10 at 80 kilos"
            </Text>
          </View>

          <View className="px-5 pt-4">
            <TextInput
              className="bg-gray-50 rounded-2xl px-5 py-4"
              style={{
                fontSize: 16,
                lineHeight: 24,
                color: colors.text,
                minHeight: 140,
              }}
              value={text}
              onChangeText={setText}
              placeholder="What happened?"
              placeholderTextColor={colors.textTertiary}
              multiline
              numberOfLines={5}
              textAlignVertical="top"
              autoFocus
            />
          </View>

          {/* Footer */}
          <View className="px-5 pt-4 pb-8 border-t border-gray-100 mt-4">
            <View className="flex-row justify-end gap-3">
              <Pressable
                onPress={onClose}
                disabled={isSaving}
                className="px-6 py-3 rounded-xl bg-gray-100"
              >
                <Text style={{ fontSize: 15, fontWeight: "700", color: colors.textSecondary }}>
                  Cancel
                </Text>
              </Pressable>
              <Pressable
                onPress={() => onSave(text.trim())}
                disabled={!canSave}
                className="px-6 py-3 rounded-xl"
                style={{
                  backgroundColor: colors.primary,
                  opacity: canSave ? 1 : 0.5,
                }}
              >
                <Text style={{ fontSize: 15, fontWeight: "700", color: "#FFFFFF" }}>
                  {isSaving ? "Saving..." : "Save"}
                </Text>
              </Pressable>
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
