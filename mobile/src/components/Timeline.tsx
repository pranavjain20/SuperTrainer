/**
 * Live session timeline — shows exercise/observation cards as they're
 * created from voice clips, plus processing state and clarifications.
 *
 * Uses ScrollView (not FlatList) because entry count per session is
 * small (<30). Auto-scrolls to bottom when entries change or processing starts.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, Text, View } from "react-native";
import { useQueryClient } from "@tanstack/react-query";

import { processTextEntry } from "@/src/api/voice";
import { ClarificationModal } from "@/src/components/ClarificationModal";
import { EmptyState } from "@/src/components/EmptyState";
import { EntryCard } from "@/src/components/EntryCard";
import { ManualEntryModal } from "@/src/components/ManualEntryModal";
import { colors } from "@/src/constants/colors";
import { useEditableEntries } from "@/src/hooks/useEditableEntries";
import { useSessionEntries } from "@/src/hooks/useSessionEntries";
import { useSessionStore } from "@/src/stores/sessionStore";
import { numberExercises } from "@/src/utils/sessions";

interface TimelineProps {
  sessionId: string;
  onRetry: (audioUri: string) => void;
  onStartRecording?: () => void;
  bottomPadding?: number;
}

export function Timeline({ sessionId, onRetry, onStartRecording, bottomPadding = 120 }: TimelineProps) {
  const scrollRef = useRef<ScrollView>(null);

  const entriesQuery = useSessionEntries(sessionId);
  const entries = entriesQuery.data ?? [];

  const { setEditingEntry, editModals } = useEditableEntries(sessionId);

  const isProcessing = useSessionStore((s) => s.isProcessing);
  const processingError = useSessionStore((s) => s.processingError);
  const failedAudioUri = useSessionStore((s) => s.failedAudioUri);
  const clearError = useSessionStore((s) => s.clearError);
  const clarifications = useSessionStore((s) => s.clarifications);
  const clearClarifications = useSessionStore((s) => s.clearClarifications);
  const finishProcessing = useSessionStore((s) => s.finishProcessing);

  // ManualEntryModal state
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [isSavingManual, setIsSavingManual] = useState(false);
  const queryClient = useQueryClient();

  // ClarificationModal is driven directly by store state
  const showClarification = clarifications.length > 0;
  const clarificationReason =
    clarifications[0]?.flag_reason || "Couldn't understand the recording";

  const handleClarificationSpeakAgain = useCallback(() => {
    clearClarifications();
    onStartRecording?.();
  }, [clearClarifications, onStartRecording]);

  const handleClarificationTypeIt = useCallback(() => {
    clearClarifications();
    setShowManualEntry(true);
  }, [clearClarifications]);

  const handleClarificationCancel = useCallback(() => {
    clearClarifications();
  }, [clearClarifications]);

  const handleManualSave = useCallback(
    async (text: string) => {
      setIsSavingManual(true);
      try {
        const result = await processTextEntry(sessionId, text);

        await queryClient.invalidateQueries({
          queryKey: ["entries", "session", sessionId],
        });

        setShowManualEntry(false);

        // Only show clarifications if the parser produced nothing useful.
        // If entries were created, the trainer sees them — no need for the
        // "didn't catch that" modal on top of a successfully created card.
        if (result.entries_created.length === 0 && result.clarifications_needed.length > 0) {
          finishProcessing(result.clarifications_needed);
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to save entry";
        Alert.alert("Save Failed", msg);
      } finally {
        setIsSavingManual(false);
      }
    },
    [sessionId, queryClient, finishProcessing],
  );

  // Auto-scroll to bottom only when NEW entries arrive during recording,
  // not on initial data load (which would jump to bottom on long sessions).
  const entryCount = entries.length;
  const prevEntryCount = useRef(0);

  useEffect(() => {
    const shouldScroll =
      // New entries added during the session (not initial load from 0 → N)
      (prevEntryCount.current > 0 && entryCount > prevEntryCount.current) ||
      // Processing indicator appeared (only after initial load)
      (isProcessing && prevEntryCount.current > 0);

    prevEntryCount.current = entryCount;

    if (shouldScroll) {
      const timer = setTimeout(() => {
        scrollRef.current?.scrollToEnd({ animated: true });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [entryCount, isProcessing]);

  // Empty state — no entries and not processing
  if (entries.length === 0 && !isProcessing && !processingError) {
    return (
      <EmptyState
        icon="microphone"
        title="Ready to record"
        subtitle="Tap the mic to start recording a voice clip"
      />
    );
  }

  return (
    <>
      <ScrollView
        ref={scrollRef}
        className="flex-1"
        contentContainerStyle={{ paddingBottom: bottomPadding }}
      >
        {/* Entry cards */}
        {(() => {
          const exerciseNumbers = numberExercises(entries);
          return [...entries]
            .sort((a, b) => a.sequence_order - b.sequence_order)
            .map((entry) => (
              <EntryCard
                key={entry.id}
                entry={entry}
                exerciseNumber={exerciseNumbers.get(entry.id)}
                onPress={() => setEditingEntry(entry)}
              />
            ));
        })()}

        {/* Processing indicator */}
        {isProcessing && (
          <View className="flex-row items-center justify-center py-5">
            <ActivityIndicator size="small" color={colors.primary} />
            <Text className="text-sm font-medium text-gray-500 ml-3">
              Processing clip...
            </Text>
          </View>
        )}

        {/* Error row — tap to retry */}
        {processingError && failedAudioUri && (
          <Pressable
            onPress={() => {
              clearError();
              onRetry(failedAudioUri);
            }}
            className="mx-4 my-2 rounded-xl overflow-hidden"
            style={{
              backgroundColor: colors.error + "10",
              borderLeftWidth: 3,
              borderLeftColor: colors.error + "60",
            }}
          >
            <View className="px-4 py-3.5">
              <Text
                className="text-[10px] font-bold uppercase tracking-widest mb-2"
                style={{ color: colors.error }}
              >
                Processing Failed
              </Text>
              <Text className="text-[13px] text-gray-700 leading-5 font-medium">
                {processingError}
              </Text>
              <Text className="text-xs font-bold mt-2" style={{ color: colors.primary }}>
                Tap to retry
              </Text>
            </View>
          </Pressable>
        )}
      </ScrollView>

      {editModals}

      <ClarificationModal
        visible={showClarification}
        reason={clarificationReason}
        onSpeakAgain={handleClarificationSpeakAgain}
        onTypeIt={handleClarificationTypeIt}
        onCancel={handleClarificationCancel}
      />

      {showManualEntry && (
        <ManualEntryModal
          visible
          isSaving={isSavingManual}
          onSave={handleManualSave}
          onClose={() => !isSavingManual && setShowManualEntry(false)}
        />
      )}
    </>
  );
}
