/**
 * Plan creation/edit screen.
 *
 * Two modes determined by state:
 *   Input mode — text area + voice button for natural language input
 *   Edit mode — parsed exercises as editable rows (after AI parse or loading existing plan)
 *
 * Route params:
 *   clientId (always) — which client this plan is for
 *   planId (optional) — edit existing plan
 */

import FontAwesome from "@expo/vector-icons/FontAwesome";
import DateTimePicker from "@react-native-community/datetimepicker";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  TextInput,
  View,
} from "react-native";

import { getPlan, parsePlanText } from "@/src/api/plans";
import { transcribeAudio } from "@/src/api/voice";
import type { PlannedExercise, PlannedExercisesPayload } from "@/src/api/types";
import { ThemedText } from "@/src/components/ThemedText";
import { cardBorder } from "@/src/constants/styles";
import { colors } from "@/src/constants/tokens";
import { useVoiceRecorder } from "@/src/hooks/useVoiceRecorder";
import { useCreatePlan, useDeletePlan, useParsePlan, useUpdatePlan } from "@/src/hooks/usePlans";
import { toISODateString } from "@/src/utils/dates";

type Mode = "input" | "edit";

/**
 * Format a date as "Wed, Apr 16" for display.
 */
function formatDateShort(date: Date): string {
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

/**
 * Format raw transcript into readable lines.
 * Splits on periods, commas before exercise-like words, and "and" conjunctions
 * so the trainer can scan each exercise separately.
 */
function formatTranscript(text: string): string {
  return text
    // Split on periods
    .replace(/\.\s*/g, ".\n")
    // Split on commas followed by a number or exercise-like word
    .replace(/,\s*(\d)/g, ",\n$1")
    // Split on " and " between exercises (but not within a phrase like "4 and a half")
    .replace(/\s+and\s+(\d)/gi, "\n$1")
    .trim();
}

export default function PlanFormScreen() {
  const router = useRouter();
  const { clientId, planId } = useLocalSearchParams<{ clientId: string; planId?: string }>();
  const isEditing = !!planId;

  // State
  const [mode, setMode] = useState<Mode>(isEditing ? "edit" : "input");
  const [planText, setPlanText] = useState("");
  const [workoutType, setWorkoutType] = useState("");
  const [exercises, setExercises] = useState<PlannedExercise[]>([]);
  const [plannedDate, setPlannedDate] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [loadingPlan, setLoadingPlan] = useState(isEditing);

  // Hooks
  const recorder = useVoiceRecorder();
  const createPlan = useCreatePlan(clientId);
  const updatePlan = useUpdatePlan(clientId);
  const deletePlan = useDeletePlan(clientId);
  const parsePlan = useParsePlan();

  // Load existing plan for editing
  useEffect(() => {
    if (!planId) return;
    (async () => {
      try {
        const plan = await getPlan(planId);
        setPlanText(plan.plan_text);
        if (plan.planned_for_date) {
          setPlannedDate(new Date(plan.planned_for_date + "T00:00:00"));
        }
        if (plan.planned_exercises) {
          const pe = plan.planned_exercises as PlannedExercisesPayload;
          setWorkoutType(pe.workout_type ?? "");
          setExercises(pe.exercises ?? []);
          setMode("edit");
        } else {
          // Legacy plan — show text in input mode
          setMode("input");
        }
      } catch {
        Alert.alert("Error", "Failed to load plan");
        router.back();
      } finally {
        setLoadingPlan(false);
      }
    })();
  }, [planId]);

  // Voice recording flow — transcribe then auto-parse into exercises
  const handleVoiceToggle = useCallback(async () => {
    if (recorder.isRecording) {
      const uri = await recorder.stopRecording();
      if (!uri) return;

      setIsTranscribing(true);
      try {
        // Step 1: Transcribe audio → text
        const result = await transcribeAudio(uri);
        const transcript = result.transcript;
        setPlanText(transcript);

        // Step 2: Auto-parse transcript → structured exercises
        const parsed = await parsePlanText(transcript);
        setWorkoutType(parsed.workout_type ?? "");
        setExercises(parsed.exercises);
        setMode("edit");
      } catch {
        Alert.alert("Error", "Failed to process voice recording");
      } finally {
        setIsTranscribing(false);
        recorder.resetRecording();
      }
    } else {
      await recorder.startRecording();
    }
  }, [recorder]);

  // Parse natural language → structured exercises
  const handleParse = useCallback(async () => {
    if (!planText.trim()) {
      Alert.alert("Empty Plan", "Type or speak your plan first.");
      return;
    }

    parsePlan.mutate(planText, {
      onSuccess: (result) => {
        setWorkoutType(result.workout_type ?? "");
        setExercises(result.exercises);
        setMode("edit");
      },
    });
  }, [planText, parsePlan]);

  // Save plan
  const handleSave = useCallback(() => {
    const planned_exercises: PlannedExercisesPayload = {
      workout_type: workoutType || null,
      exercises,
    };

    if (isEditing && planId) {
      updatePlan.mutate(
        {
          planId,
          data: {
            plan_text: planText,
            planned_exercises,
            planned_for_date: toISODateString(plannedDate),
          },
        },
        { onSuccess: () => router.back() },
      );
    } else {
      createPlan.mutate(
        {
          client_id: clientId,
          plan_text: planText,
          planned_exercises,
          planned_for_date: toISODateString(plannedDate),
        },
        { onSuccess: () => router.back() },
      );
    }
  }, [isEditing, planId, planText, workoutType, exercises, plannedDate, clientId, createPlan, updatePlan, router]);

  // Delete plan
  const handleDelete = useCallback(() => {
    if (!planId) return;
    Alert.alert("Delete Plan", "Are you sure you want to delete this plan?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: () => deletePlan.mutate(planId, { onSuccess: () => router.back() }),
      },
    ]);
  }, [planId, deletePlan, router]);

  // Update a single exercise field
  const updateExercise = useCallback((index: number, field: keyof PlannedExercise, value: string) => {
    setExercises((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  }, []);

  // Delete exercise row
  const deleteExercise = useCallback((index: number) => {
    setExercises((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // Add exercise from inline text input (e.g., "Hip Thrusts 3x12")
  const [addText, setAddText] = useState("");
  const [isAddRecording, setIsAddRecording] = useState(false);
  const [isAddTranscribing, setIsAddTranscribing] = useState(false);

  const addExerciseFromText = useCallback(() => {
    const text = addText.trim();
    if (!text) return;

    // Parse "Hip Thrusts 3x12 at 20kg" → name, sets, reps, weight
    // Or just "Plank" → name only
    const match = text.match(/^(.+?)\s+(\d.*)$/);
    if (match) {
      const name = match[1].trim();
      const rest = match[2].trim();
      // Try to parse "3x12 at 20kg" or "3x12" or "4 sets"
      const setsReps = rest.match(/^(\d+)\s*[xX×]\s*(\d+)/);
      const weightMatch = rest.match(/(?:at|@)\s*(.+)$/i);
      setExercises((prev) => [...prev, {
        exercise_name: name,
        sets: setsReps ? setsReps[1] : "",
        reps: setsReps ? setsReps[2] : rest,
        weight: weightMatch ? weightMatch[1].trim() : "",
      }]);
    } else {
      setExercises((prev) => [...prev, { exercise_name: text, sets: "", reps: "", weight: "" }]);
    }
    setAddText("");
  }, [addText]);

  // Voice add — record a single exercise, transcribe, parse, add
  const handleAddVoice = useCallback(async () => {
    if (recorder.isRecording) {
      const uri = await recorder.stopRecording();
      setIsAddRecording(false);
      if (!uri) return;

      setIsAddTranscribing(true);
      try {
        const result = await transcribeAudio(uri);
        const parsed = await parsePlanText(result.transcript);
        if (parsed.exercises.length > 0) {
          setExercises((prev) => [...prev, ...parsed.exercises]);
        } else {
          // Fallback: put transcript in the add input
          setAddText(result.transcript);
        }
      } catch {
        Alert.alert("Error", "Failed to process voice");
      } finally {
        setIsAddTranscribing(false);
        recorder.resetRecording();
      }
    } else {
      setIsAddRecording(true);
      await recorder.startRecording();
    }
  }, [recorder]);

  const isSaving = createPlan.isPending || updatePlan.isPending;

  if (loadingPlan) {
    return (
      <View className="flex-1 items-center justify-center" style={{ backgroundColor: colors.bg.base }}>
        <ActivityIndicator size="large" color={colors.blue[500]} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      className="flex-1"
      style={{ backgroundColor: colors.bg.base }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView className="flex-1" keyboardShouldPersistTaps="handled">
        {/* Header */}
        <View className="pt-16 pb-2 px-5">
          <Pressable onPress={() => router.back()} className="mb-4" hitSlop={12}>
            <FontAwesome name="arrow-left" size={20} color={colors.text.primary} />
          </Pressable>
          <ThemedText variant="title-1" color={colors.text.primary}>
            {isEditing ? "Edit Plan" : "New Plan"}
          </ThemedText>
        </View>

        {/* Date — compact pill, tap to change */}
        <View className="mx-5 mb-4 flex-row items-center">
          <Pressable
            onPress={() => setShowDatePicker((v) => !v)}
            className="rounded-full px-4 py-2 flex-row items-center"
            style={{ backgroundColor: colors.bg.surface2 }}
          >
            <FontAwesome name="calendar-o" size={13} color={colors.blue[500]} style={{ marginRight: 8 }} />
            <ThemedText variant="body-small" color={colors.text.primary} style={{ fontFamily: "Inter-SemiBold" }}>
              {formatDateShort(plannedDate)}
            </ThemedText>
          </Pressable>
        </View>

        {showDatePicker && (
          <DateTimePicker
            value={plannedDate}
            mode="date"
            display="spinner"
            themeVariant="dark"
            onChange={(_, date) => {
              setShowDatePicker(false);
              if (date) setPlannedDate(date);
            }}
          />
        )}

        {mode === "input" ? (
          /* ---- INPUT MODE ---- */
          <View className="mx-5">
            {/* Text area */}
            <View
              className="rounded-xl overflow-hidden mb-4"
              style={{ backgroundColor: colors.bg.surface1, ...cardBorder }}
            >
              <TextInput
                value={planText}
                onChangeText={setPlanText}
                placeholder={"Type or speak your plan...\ne.g., Squats 4 sets of 8, Lunges 3 sets of 10"}
                placeholderTextColor={colors.text.tertiary}
                multiline
                textAlignVertical="top"
                autoFocus={!isEditing}
                style={{
                  color: colors.text.primary,
                  fontFamily: "Inter-Regular",
                  fontSize: 16,
                  lineHeight: 26,
                  padding: 16,
                  minHeight: 160,
                }}
              />
            </View>

            {/* Voice record button */}
            <Pressable
              onPress={handleVoiceToggle}
              disabled={isTranscribing}
              className="rounded-xl py-4 flex-row items-center justify-center mb-4"
              style={{
                backgroundColor: recorder.isRecording ? colors.recording.red : colors.bg.surface2,
                opacity: isTranscribing ? 0.6 : 1,
              }}
            >
              {isTranscribing ? (
                <>
                  <ActivityIndicator size="small" color={colors.text.primary} />
                  <ThemedText variant="body-medium" color={colors.text.primary} style={{ marginLeft: 10 }}>
                    Transcribing...
                  </ThemedText>
                </>
              ) : (
                <>
                  <FontAwesome
                    name={recorder.isRecording ? "stop" : "microphone"}
                    size={18}
                    color={colors.text.primary}
                  />
                  <ThemedText variant="body-medium" color={colors.text.primary} style={{ marginLeft: 10 }}>
                    {recorder.isRecording ? `Recording (${recorder.duration}s)` : "Speak your plan"}
                  </ThemedText>
                </>
              )}
            </Pressable>

            {/* Parse / Create button */}
            <Pressable
              onPress={handleParse}
              disabled={parsePlan.isPending || !planText.trim()}
              className="rounded-xl py-4 items-center"
              style={{
                backgroundColor: planText.trim() ? colors.blue[500] : colors.bg.surface2,
                opacity: parsePlan.isPending ? 0.6 : 1,
              }}
            >
              {parsePlan.isPending ? (
                <ActivityIndicator size="small" color={colors.text.primary} />
              ) : (
                <ThemedText
                  variant="body-medium"
                  color={planText.trim() ? colors.text.inverse : colors.text.tertiary}
                  style={{ fontFamily: "Inter-Bold" }}
                >
                  Create Plan
                </ThemedText>
              )}
            </Pressable>
          </View>
        ) : (
          /* ---- EDIT MODE ---- */
          <View className="mx-5">
            {/* Workout type */}
            <TextInput
              value={workoutType}
              onChangeText={setWorkoutType}
              placeholder="Workout name"
              placeholderTextColor={colors.text.tertiary}
              style={{
                color: colors.text.primary,
                fontFamily: "Inter-Bold",
                fontSize: 18,
                backgroundColor: colors.bg.surface1,
                borderRadius: 10,
                paddingHorizontal: 14,
                paddingVertical: 12,
                marginBottom: 16,
                ...cardBorder,
              }}
            />

            {/* Exercise cards */}
            {exercises.map((ex, i) => (
              <View
                key={`ex-${i}`}
                className="rounded-xl mb-3"
                style={{ backgroundColor: colors.bg.surface1, ...cardBorder }}
              >
                {/* Header: number + delete */}
                <View className="flex-row items-center justify-between px-4 pt-3 pb-1">
                  <ThemedText variant="caption" color={colors.text.tertiary}>
                    EXERCISE {i + 1}
                  </ThemedText>
                  <Pressable onPress={() => deleteExercise(i)} hitSlop={12}>
                    <FontAwesome name="trash-o" size={15} color={colors.red[500]} />
                  </Pressable>
                </View>

                {/* Exercise name */}
                <View className="px-4 pt-1 pb-2">
                  <TextInput
                    value={ex.exercise_name}
                    onChangeText={(v) => updateExercise(i, "exercise_name", v)}
                    placeholder="Exercise name"
                    placeholderTextColor={colors.text.tertiary}
                    style={{
                      color: colors.text.primary,
                      fontFamily: "Inter-Bold",
                      fontSize: 17,
                      backgroundColor: colors.bg.surface2,
                      borderRadius: 8,
                      paddingHorizontal: 12,
                      paddingVertical: 9,
                    }}
                  />
                </View>

                {/* Sets / Reps / Weight — three inline fields */}
                <View className="flex-row px-4 pb-3" style={{ gap: 8 }}>
                  {/* Sets */}
                  <View style={{ flex: 1 }}>
                    <ThemedText variant="body-small" color={colors.text.tertiary} style={{ fontSize: 11, marginBottom: 3, marginLeft: 4 }}>
                      Sets
                    </ThemedText>
                    <TextInput
                      value={ex.sets}
                      onChangeText={(v) => updateExercise(i, "sets", v)}
                      placeholder="—"
                      placeholderTextColor={colors.text.tertiary}
                      keyboardType="default"
                      style={{
                        color: colors.blue[400],
                        fontFamily: "Inter-SemiBold",
                        fontSize: 15,
                        backgroundColor: colors.bg.surface2,
                        borderRadius: 8,
                        paddingHorizontal: 10,
                        paddingVertical: 8,
                        textAlign: "center",
                      }}
                    />
                  </View>

                  {/* Reps */}
                  <View style={{ flex: 2 }}>
                    <ThemedText variant="body-small" color={colors.text.tertiary} style={{ fontSize: 11, marginBottom: 3, marginLeft: 4 }}>
                      Reps
                    </ThemedText>
                    <TextInput
                      value={ex.reps}
                      onChangeText={(v) => updateExercise(i, "reps", v)}
                      placeholder="—"
                      placeholderTextColor={colors.text.tertiary}
                      style={{
                        color: colors.blue[400],
                        fontFamily: "Inter-SemiBold",
                        fontSize: 15,
                        backgroundColor: colors.bg.surface2,
                        borderRadius: 8,
                        paddingHorizontal: 10,
                        paddingVertical: 8,
                        textAlign: "center",
                      }}
                    />
                  </View>

                  {/* Weight */}
                  <View style={{ flex: 2 }}>
                    <ThemedText variant="body-small" color={colors.text.tertiary} style={{ fontSize: 11, marginBottom: 3, marginLeft: 4 }}>
                      Weight
                    </ThemedText>
                    <TextInput
                      value={ex.weight}
                      onChangeText={(v) => updateExercise(i, "weight", v)}
                      placeholder="—"
                      placeholderTextColor={colors.text.tertiary}
                      style={{
                        color: colors.blue[400],
                        fontFamily: "Inter-SemiBold",
                        fontSize: 15,
                        backgroundColor: colors.bg.surface2,
                        borderRadius: 8,
                        paddingHorizontal: 10,
                        paddingVertical: 8,
                        textAlign: "center",
                      }}
                    />
                  </View>
                </View>
              </View>
            ))}

            {/* Add exercise */}
            <View
              className="rounded-xl mb-5"
              style={{ backgroundColor: colors.bg.surface1, ...cardBorder }}
            >
              <View className="px-4 pt-3 pb-2">
                <TextInput
                  value={addText}
                  onChangeText={setAddText}
                  onSubmitEditing={addExerciseFromText}
                  placeholder="Add exercise, e.g. Hip Thrusts 3x12"
                  placeholderTextColor={colors.text.tertiary}
                  returnKeyType="done"
                  blurOnSubmit={false}
                  style={{
                    color: colors.text.primary,
                    fontFamily: "Inter-Regular",
                    fontSize: 16,
                    backgroundColor: colors.bg.surface2,
                    borderRadius: 8,
                    paddingHorizontal: 12,
                    paddingVertical: 10,
                  }}
                />
              </View>
              <View className="flex-row px-4 pb-3" style={{ gap: 10 }}>
                <Pressable
                  onPress={addExerciseFromText}
                  className="flex-1 rounded-lg py-3 items-center"
                  style={{ backgroundColor: addText.trim() ? colors.blue[500] : colors.bg.surface2 }}
                >
                  <ThemedText
                    variant="body-small"
                    color={addText.trim() ? colors.text.inverse : colors.text.tertiary}
                    style={{ fontFamily: "Inter-Bold" }}
                  >
                    + Add
                  </ThemedText>
                </Pressable>
                <Pressable
                  onPress={handleAddVoice}
                  disabled={isAddTranscribing}
                  className="flex-1 rounded-lg py-3 flex-row items-center justify-center"
                  style={{ backgroundColor: isAddRecording ? colors.recording.red : colors.blue[600] }}
                >
                  {isAddTranscribing ? (
                    <ActivityIndicator size="small" color={colors.text.primary} />
                  ) : (
                    <>
                      <FontAwesome
                        name={isAddRecording ? "stop" : "microphone"}
                        size={14}
                        color={colors.text.primary}
                      />
                      <ThemedText variant="body-small" color={colors.text.primary} style={{ fontFamily: "Inter-Bold", marginLeft: 8 }}>
                        {isAddRecording ? "Stop" : "Speak"}
                      </ThemedText>
                    </>
                  )}
                </Pressable>
              </View>
            </View>

            {/* Save button */}
            <Pressable
              onPress={handleSave}
              disabled={isSaving || exercises.length === 0}
              className="rounded-xl py-4 items-center mb-4"
              style={{
                backgroundColor: exercises.length > 0 ? colors.blue[500] : colors.bg.surface2,
                opacity: isSaving ? 0.6 : 1,
              }}
            >
              {isSaving ? (
                <ActivityIndicator size="small" color={colors.text.primary} />
              ) : (
                <ThemedText
                  variant="body-medium"
                  color={exercises.length > 0 ? colors.text.inverse : colors.text.tertiary}
                  style={{ fontFamily: "Inter-Bold" }}
                >
                  Save Plan
                </ThemedText>
              )}
            </Pressable>

            {/* Secondary actions */}
            <View className="flex-row justify-center" style={{ gap: 20 }}>
              <Pressable onPress={() => setMode("input")} className="py-2">
                <ThemedText variant="body-small" color={colors.text.tertiary}>
                  Start over
                </ThemedText>
              </Pressable>
              {isEditing && (
                <Pressable
                  onPress={handleDelete}
                  disabled={deletePlan.isPending}
                  className="py-2"
                >
                  <ThemedText variant="body-small" color={colors.red[500]}>
                    Delete plan
                  </ThemedText>
                </Pressable>
              )}
            </View>
          </View>
        )}

        {/* Bottom padding */}
        <View style={{ height: 40 }} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
