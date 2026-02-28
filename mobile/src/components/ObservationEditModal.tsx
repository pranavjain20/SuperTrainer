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
  Text,
  TextInput,
  View,
} from "react-native";

import type { SessionEntry, SessionEntryUpdate } from "@/src/api/types";
import { colors, FLAG_COLORS } from "@/src/constants/colors";

const FLAG_OPTIONS = [
  { key: null, label: "None", color: colors.textTertiary },
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
        <Pressable className="flex-1" onPress={isSaving ? undefined : onClose} />

        {/* Sheet */}
        <View className="bg-white rounded-t-3xl">
          {/* Header */}
          <View className="px-5 pt-5 pb-3 border-b border-gray-100">
            <Text className="text-lg font-bold text-gray-900">Edit Observation</Text>
          </View>

          <View className="px-5 pt-4">
            {/* Observation text */}
            <TextInput
              className="bg-gray-50 rounded-xl px-4 py-3 text-sm text-gray-900 font-medium mb-5"
              value={observationText}
              onChangeText={setObservationText}
              placeholder="What did you observe?"
              placeholderTextColor={colors.textTertiary}
              multiline
              numberOfLines={4}
              textAlignVertical="top"
              style={{ minHeight: 100 }}
            />

            {/* Flag color picker */}
            <Text className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
              Flag
            </Text>
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
                        backgroundColor: opt.color + (opt.key ? "20" : "10"),
                        borderWidth: isSelected ? 2.5 : 1,
                        borderColor: isSelected ? opt.color : opt.color + "40",
                      }}
                    >
                      <View
                        className="w-4 h-4 rounded-full"
                        style={{ backgroundColor: opt.color }}
                      />
                    </View>
                    <Text
                      className="text-[10px] mt-1 font-medium"
                      style={{ color: isSelected ? opt.color : colors.textTertiary }}
                    >
                      {opt.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </View>

          {/* Footer */}
          <View className="px-5 pt-4 pb-8 border-t border-gray-100">
            <View className="flex-row justify-between items-center">
              <Pressable onPress={confirmDelete} disabled={isSaving} hitSlop={12}>
                <Text style={{ fontSize: 15, fontWeight: "700", color: colors.error }}>
                  Delete
                </Text>
              </Pressable>

              <View className="flex-row gap-3">
                <Pressable
                  onPress={onClose}
                  disabled={isSaving}
                  className="px-6 py-3 rounded-xl bg-gray-100"
                >
                  <Text style={{ fontSize: 15, fontWeight: "700", color: colors.textSecondary }}>Cancel</Text>
                </Pressable>
                <Pressable
                  onPress={handleSave}
                  disabled={isSaving}
                  className="px-6 py-3 rounded-xl"
                  style={{ backgroundColor: colors.primary, opacity: isSaving ? 0.5 : 1 }}
                >
                  <Text style={{ fontSize: 15, fontWeight: "700", color: "#FFFFFF" }}>
                    {isSaving ? "Saving..." : "Save"}
                  </Text>
                </Pressable>
              </View>
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}
