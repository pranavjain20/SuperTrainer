/**
 * Modal for inline-editing an exercise card.
 *
 * Renders a scrollable form with exercise name + one row per set.
 * All fields are strings while editing, parsed to numbers on save.
 * Normalizes weight to { weight, weight_unit: "kg" } (voice format).
 */

import { useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

import type { SessionEntry, SessionEntryUpdate, SetData } from "@/src/api/types";
import { colors } from "@/src/constants/colors";
import { capitalizeWords } from "@/src/utils/strings";

interface SetFormData {
  reps: string;
  weight: string;
  rpe: string;
  notes: string;
}

interface ExerciseEditModalProps {
  entry: SessionEntry;
  visible: boolean;
  isSaving: boolean;
  onSave: (data: SessionEntryUpdate) => void;
  onDelete: () => void;
  onClose: () => void;
}

function initSets(sets: SetData[]): SetFormData[] {
  return sets.map((s) => ({
    reps: s.reps != null ? String(s.reps) : "",
    weight: String(s.weight ?? s.weight_kg ?? ""),
    rpe: s.rpe != null ? String(s.rpe) : "",
    notes: s.notes ?? "",
  }));
}

function parseNum(s: string): number | null {
  const n = parseFloat(s);
  return Number.isNaN(n) ? null : n;
}

export function ExerciseEditModal({
  entry,
  visible,
  isSaving,
  onSave,
  onDelete,
  onClose,
}: ExerciseEditModalProps) {
  const [exerciseName, setExerciseName] = useState(
    capitalizeWords(entry.exercise_name ?? entry.exercise_canonical ?? ""),
  );
  const [sets, setSets] = useState<SetFormData[]>(initSets(entry.sets ?? []));

  const updateSet = (index: number, field: keyof SetFormData, value: string) => {
    setSets((prev) => prev.map((s, i) => (i === index ? { ...s, [field]: value } : s)));
  };

  const handleSave = () => {
    const originalSets = entry.sets ?? [];
    const parsedSets: SetData[] = sets.map((s, i) => {
      // Spread original to preserve rir, equipment_note, duration_seconds, etc.
      // Delete weight_kg so we normalize seed format → voice format (weight + weight_unit)
      const { weight_kg: _drop, ...preserved } = originalSets[i] ?? {};
      return {
        ...preserved,
        set: i + 1,
        reps: parseNum(s.reps),
        weight: parseNum(s.weight),
        weight_unit: "kg",
        rpe: parseNum(s.rpe),
        notes: s.notes.trim() || null,
      };
    });

    onSave({
      exercise_name: exerciseName.trim() || undefined,
      sets: parsedSets,
    });
  };

  const confirmDelete = () => {
    Alert.alert("Delete Exercise", "This entry will be permanently removed.", [
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
        <View className="bg-white rounded-t-3xl" style={{ maxHeight: "85%" }}>
          {/* Header */}
          <View className="px-5 pt-5 pb-3 border-b border-gray-100">
            <Text className="text-lg font-bold text-gray-900">Edit Exercise</Text>
          </View>

          <ScrollView className="px-5 pt-4 pb-2" keyboardShouldPersistTaps="handled">
            {/* Exercise name */}
            <Text style={{ fontSize: 13, fontWeight: "700", color: colors.textSecondary, marginBottom: 6 }}>
              Exercise Name
            </Text>
            <TextInput
              className="bg-gray-50 rounded-xl px-4 py-3.5 mb-5"
              style={{ fontSize: 18, fontWeight: "700", color: colors.text }}
              value={exerciseName}
              onChangeText={setExerciseName}
              autoCapitalize="words"
              placeholder="e.g. Bench Press"
              placeholderTextColor={colors.textTertiary}
            />

            {/* Sets */}
            {sets.map((set, i) => (
              <View key={i} className="mb-5">
                <Text style={{ fontSize: 13, fontWeight: "700", color: colors.textSecondary, marginBottom: 8 }}>
                  Set {i + 1}
                </Text>
                <View className="flex-row gap-2">
                  <View className="flex-1">
                    <Text style={{ fontSize: 12, fontWeight: "600", color: colors.textSecondary, marginBottom: 4 }}>
                      Reps
                    </Text>
                    <TextInput
                      className="bg-gray-50 rounded-lg px-3 py-3 text-center"
                      style={{ fontSize: 17, fontWeight: "700", color: colors.text }}
                      value={set.reps}
                      onChangeText={(v) => updateSet(i, "reps", v)}
                      keyboardType="numeric"
                      placeholder="—"
                      placeholderTextColor={colors.textTertiary}
                    />
                  </View>
                  <View className="flex-1">
                    <Text style={{ fontSize: 12, fontWeight: "600", color: colors.textSecondary, marginBottom: 4 }}>
                      Weight (kg)
                    </Text>
                    <TextInput
                      className="bg-gray-50 rounded-lg px-3 py-3 text-center"
                      style={{ fontSize: 17, fontWeight: "700", color: colors.text }}
                      value={set.weight}
                      onChangeText={(v) => updateSet(i, "weight", v)}
                      keyboardType="decimal-pad"
                      placeholder="—"
                      placeholderTextColor={colors.textTertiary}
                    />
                  </View>
                  <View className="flex-1">
                    <Text style={{ fontSize: 12, fontWeight: "600", color: colors.textSecondary, marginBottom: 4 }}>
                      RPE
                    </Text>
                    <TextInput
                      className="bg-gray-50 rounded-lg px-3 py-3 text-center"
                      style={{ fontSize: 17, fontWeight: "700", color: colors.text }}
                      value={set.rpe}
                      onChangeText={(v) => updateSet(i, "rpe", v)}
                      keyboardType="numeric"
                      placeholder="—"
                      placeholderTextColor={colors.textTertiary}
                    />
                  </View>
                </View>
                <View className="mt-2">
                  <Text style={{ fontSize: 12, fontWeight: "600", color: colors.textSecondary, marginBottom: 4 }}>
                    Notes
                  </Text>
                  <TextInput
                    className="bg-gray-50 rounded-lg px-3 py-3"
                    style={{ fontSize: 15, fontWeight: "500", color: colors.text }}
                    value={set.notes}
                    onChangeText={(v) => updateSet(i, "notes", v)}
                    placeholder="Optional"
                    placeholderTextColor={colors.textTertiary}
                  />
                </View>
              </View>
            ))}
          </ScrollView>

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
