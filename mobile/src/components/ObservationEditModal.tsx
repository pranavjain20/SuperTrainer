/**
 * Modal for inline-editing an observation card.
 *
 * Simple text area + flag color picker (row of colored circles).
 * Clearing the flag also clears flag_reason.
 */

import { useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  TextInput,
  View,
} from "react-native";

import type { SessionEntry, SessionEntryUpdate } from "@/src/api/types";
import { ThemedText } from "@/src/components/ThemedText";
import { colors, FLAG_COLORS } from "@/src/constants/tokens";

const FLAG_OPTIONS = [
  { key: null, label: "None", color: colors.text.tertiary },
  { key: "green", label: "Green", color: FLAG_COLORS.green },
  { key: "yellow", label: "Yellow", color: FLAG_COLORS.yellow },
  { key: "red", label: "Red", color: FLAG_COLORS.red },
] as const;

interface ObservationEditModalProps {
  entry: SessionEntry;
  visible: boolean;
  isSaving: boolean;
  onSave: (data: SessionEntryUpdate) => void;
  onDelete: () => void;
  onClose: () => void;
}

export function ObservationEditModal({
  entry,
  visible,
  isSaving,
  onSave,
  onDelete,
  onClose,
}: ObservationEditModalProps) {
  const [observationText, setObservationText] = useState(entry.observation_text ?? "");
  const [flagColor, setFlagColor] = useState<string | null>(entry.flag_color);

  const handleSave = () => {
    // Backend uses exclude_unset=True — undefined = no change, null = clear.
    const data: SessionEntryUpdate = {
      observation_text: observationText.trim() || null,
      flag_color: flagColor,
    };
    // Clearing the flag also clears flag_reason
    if (!flagColor && entry.flag_color) {
      data.flag_reason = null;
    }
    onSave(data);
  };

  const confirmDelete = () => {
    Alert.alert("Delete Observation", "This entry will be permanently removed.", [
      { text: "Cancel", style: "cancel" },
      { text: "Delete", style: "destructive", onPress: onDelete },
    ]);
  };

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
            <ThemedText variant="title-2">Edit Observation</ThemedText>
          </View>

          <View className="px-5 pt-4">
            {/* Observation text */}
            <TextInput
              className="rounded-xl px-4 py-3 mb-5"
              style={{ backgroundColor: colors.bg.surface2, fontSize: 14, fontFamily: "Inter-Medium", color: colors.text.primary, minHeight: 100 }}
              value={observationText}
              onChangeText={setObservationText}
              placeholder="What did you observe?"
              placeholderTextColor={colors.text.tertiary}
              multiline
              numberOfLines={4}
              textAlignVertical="top"
            />

            {/* Flag color picker */}
            <ThemedText variant="caption" color={colors.text.tertiary} style={{ marginBottom: 12 }}>
              Flag
            </ThemedText>
            <View className="flex-row gap-3 mb-5">
              {FLAG_OPTIONS.map((opt) => {
                const isSelected = flagColor === opt.key;
                return (
                  <Pressable
                    key={opt.key ?? "none"}
                    onPress={() => setFlagColor(opt.key)}
                    className="items-center"
                  >
                    <View
                      className="w-9 h-9 rounded-full items-center justify-center"
                      style={{
                        backgroundColor: opt.color + (opt.key ? "30" : "15"),
                        borderWidth: isSelected ? 2.5 : 1,
                        borderColor: isSelected ? opt.color : opt.color + "50",
                      }}
                    >
                      <View
                        className="w-4 h-4 rounded-full"
                        style={{ backgroundColor: opt.color }}
                      />
                    </View>
                    <ThemedText
                      variant="small"
                      color={isSelected ? opt.color : colors.text.tertiary}
                      style={{ marginTop: 4, fontSize: 10 }}
                    >
                      {opt.label}
                    </ThemedText>
                  </Pressable>
                );
              })}
            </View>
          </View>

          {/* Footer */}
          <View className="px-5 pt-4 pb-8" style={{ borderTopWidth: 1, borderTopColor: colors.border.subtle }}>
            <View className="flex-row justify-between items-center">
              <Pressable onPress={confirmDelete} disabled={isSaving} hitSlop={12}>
                <ThemedText variant="body-medium" color={colors.red[500]}>
                  Delete
                </ThemedText>
              </Pressable>

              <View className="flex-row gap-3">
                <Pressable
                  onPress={onClose}
                  disabled={isSaving}
                  className="px-6 py-3 rounded-xl"
                  style={{ backgroundColor: colors.bg.surface2 }}
                >
                  <ThemedText variant="body-medium" color={colors.text.secondary}>Cancel</ThemedText>
                </Pressable>
                <Pressable
                  onPress={handleSave}
                  disabled={isSaving}
                  className="px-6 py-3 rounded-xl"
                  style={{ backgroundColor: colors.blue[500], opacity: isSaving ? 0.5 : 1 }}
                >
                  <ThemedText variant="body-medium" color={colors.text.inverse}>
                    {isSaving ? "Saving..." : "Save"}
                  </ThemedText>
                </Pressable>
              </View>
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
