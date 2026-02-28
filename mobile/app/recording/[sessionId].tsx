import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useLocalSearchParams, useNavigation, useRouter } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ConfirmSheet } from "@/src/components/ConfirmSheet";
import { EntryCard } from "@/src/components/EntryCard";
import { ErrorState } from "@/src/components/ErrorState";
import { LoadingState } from "@/src/components/LoadingState";
import { RecordButton } from "@/src/components/RecordButton";
import { SessionHeader } from "@/src/components/SessionHeader";
import { SessionSummary } from "@/src/components/SessionSummary";
import { Timeline } from "@/src/components/Timeline";
import { colors } from "@/src/constants/colors";
import { cardShadow } from "@/src/constants/styles";
import { useClient } from "@/src/hooks/useClient";
import { useEditableEntries } from "@/src/hooks/useEditableEntries";
import { useEndSession } from "@/src/hooks/useEndSession";
import { useSession } from "@/src/hooks/useSession";
import { useSessionEntries } from "@/src/hooks/useSessionEntries";
import { useVoiceClipUpload } from "@/src/hooks/useVoiceClipUpload";
import { useVoiceRecorder } from "@/src/hooks/useVoiceRecorder";
import { useRecordingStore } from "@/src/stores/recordingStore";
import { useSessionStore } from "@/src/stores/sessionStore";
import { formatTime } from "@/src/utils/dates";
import {
  computeSessionStats,
  formatSessionDuration,
  getSessionDisplay,
  numberExercises,
} from "@/src/utils/sessions";

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export default function SessionRecordingScreen() {
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const router = useRouter();
  const navigation = useNavigation();
  const insets = useSafeAreaInsets();

  const sessionQuery = useSession(sessionId);
  const clientQuery = useClient(sessionQuery.data?.client_id);
  const entriesQuery = useSessionEntries(sessionId);
  const recorder = useVoiceRecorder();
  const { upload } = useVoiceClipUpload(sessionId!);
  const isProcessing = useSessionStore((s) => s.isProcessing);
  const resetSessionStore = useSessionStore((s) => s.reset);
  const setActiveSession = useRecordingStore((s) => s.setActiveSession);
  const clearActiveSession = useRecordingStore((s) => s.clearActiveSession);

  const [showEndConfirm, setShowEndConfirm] = useState(false);

  const session = sessionQuery.data;
  const isSessionEnded = !!session?.ended_at;

  const {
    endSession,
    isEnding,
    workoutType,
    isClassifying,
  } = useEndSession({
    sessionId: sessionId!,
    isSessionEnded,
  });

  // Derived stats from entries cache
  const entries = entriesQuery.data ?? [];
  const stats = computeSessionStats(entries);


  // Editable entries (inline editing modals)
  const { setEditingEntry, editModals } = useEditableEntries(sessionId!);

  // Auto-upload when recording completes.
  const lastUploadedUri = useRef<string | null>(null);
  useEffect(() => {
    if (
      recorder.recordingUri &&
      recorder.recordingUri !== lastUploadedUri.current
    ) {
      lastUploadedUri.current = recorder.recordingUri;
      upload(recorder.recordingUri);
      recorder.resetRecording();
    }
  }, [recorder.recordingUri, upload, recorder.resetRecording]);

  // Cleanup session store on unmount
  useEffect(() => {
    return () => resetSessionStore();
  }, [resetSessionStore]);

  // Track active session for the banner (visible across all tabs).
  // Set when active, clear when session ends — but NOT on unmount,
  // because the banner must persist after navigating away.
  useEffect(() => {
    if (session && clientQuery.data && !isSessionEnded) {
      setActiveSession(sessionId!, clientQuery.data.name, session.started_at);
    } else if (isSessionEnded) {
      clearActiveSession();
    }
  }, [session, clientQuery.data, isSessionEnded, sessionId, setActiveSession, clearActiveSession]);

  // Intercept ALL back navigation when recording
  const recorderRef = useRef(recorder);
  recorderRef.current = recorder;

  useEffect(() => {
    return navigation.addListener("beforeRemove", (e) => {
      if (!recorderRef.current.isRecording) return;

      e.preventDefault();

      Alert.alert(
        "Recording in progress",
        "Going back will stop the current recording. Are you sure?",
        [
          { text: "Keep Recording", style: "cancel" },
          {
            text: "Stop & Go Back",
            style: "destructive",
            onPress: async () => {
              await recorderRef.current.stopRecording();
              navigation.dispatch(e.data.action);
            },
          },
        ],
      );
    });
  }, [navigation]);

  const handleRecordPress = async () => {
    if (recorder.isRecording) {
      await recorder.stopRecording();
    } else {
      recorder.resetRecording();
      await recorder.startRecording();
    }
  };

  const handleEndSession = useCallback(() => {
    setShowEndConfirm(false);
    clearActiveSession();
    endSession();
  }, [endSession, clearActiveSession]);

  const handleDone = useCallback(() => {
    router.back();
  }, [router]);

  // Loading
  if (sessionQuery.isLoading) {
    return (
      <View className="flex-1 bg-[#FAFAFA]">
        <LoadingState />
      </View>
    );
  }

  // Error
  if (sessionQuery.isError || !sessionQuery.data) {
    return (
      <View className="flex-1 bg-[#FAFAFA]">
        <ErrorState
          message={sessionQuery.error?.message ?? "Session not found"}
          onRetry={() => sessionQuery.refetch()}
        />
      </View>
    );
  }

  const clientName = clientQuery.data?.name ?? "Loading...";
  const status = getSessionDisplay(session!);
  const sessionTime = formatTime(session!.scheduled_for ?? session!.started_at);

  // Show "End Session" button only when active
  const showEndButton = !isSessionEnded && !recorder.isRecording && !isProcessing;

  // ---------------------------------------------------------------------------
  // Ended state — single ScrollView: Summary block → Workout Details
  // ---------------------------------------------------------------------------
  if (isSessionEnded && session!.ended_at) {
    const sortedEntries = [...entries].sort(
      (a, b) => a.sequence_order - b.sequence_order,
    );
    const exerciseNumbers = numberExercises(entries);

    return (
      <View className="flex-1 bg-[#FAFAFA]">
        <SessionHeader
          clientName={clientName}
          sessionTime={sessionTime}
          status={status}
          onBack={() => router.back()}
        />

        <ScrollView
          className="flex-1"
          contentContainerStyle={{ paddingBottom: insets.bottom + 24 }}
        >
          {/* ── Summary card (compact) ── */}
          <SessionSummary
            duration={formatSessionDuration(session!.started_at, session!.ended_at)}
            exerciseCount={stats.exerciseCount}
            totalSets={stats.totalSets}
            workoutType={workoutType}
            isClassifying={isClassifying}
          />

          {/* ── Done button ── */}
          <View className="mx-4 mt-4">
            <Pressable
              onPress={handleDone}
              className="py-4 rounded-xl items-center"
              style={{
                backgroundColor: colors.primary,
                shadowColor: colors.primary,
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.3,
                shadowRadius: 8,
                elevation: 6,
              }}
            >
              <Text style={{ fontSize: 16, fontWeight: "800", color: "#FFFFFF", letterSpacing: 0.5 }}>
                Done
              </Text>
            </Pressable>
          </View>

          {/* ── Workout Details (single container card) ── */}
          {sortedEntries.length > 0 && (
            <View
              className="mx-4 mt-5 mb-4 rounded-2xl bg-white overflow-hidden"
              style={cardShadow}
            >
              {/* Section header */}
              <View
                className="px-4 py-3"
                style={{ backgroundColor: colors.primary + "0A" }}
              >
                <Text
                  style={{
                    fontSize: 13,
                    fontWeight: "800",
                    color: colors.primary,
                    textTransform: "uppercase",
                    letterSpacing: 1.2,
                  }}
                >
                  Workout Details
                </Text>
              </View>

              {/* Entries separated by dividers */}
              {sortedEntries.map((entry, i) => (
                <View
                  key={entry.id}
                  style={i > 0 ? { borderTopWidth: 1, borderTopColor: colors.borderLight } : undefined}
                >
                  <EntryCard
                    entry={entry}
                    exerciseNumber={exerciseNumbers.get(entry.id)}
                    onPress={() => setEditingEntry(entry)}
                    contained
                  />
                </View>
              ))}
            </View>
          )}
        </ScrollView>

        {editModals}
      </View>
    );
  }

  // ---------------------------------------------------------------------------
  // Active state — recording in progress
  // ---------------------------------------------------------------------------
  return (
    <View className="flex-1 bg-[#FAFAFA]">
      <SessionHeader
        clientName={clientName}
        sessionTime={sessionTime}
        status={status}
        onBack={() => router.back()}
        showEndButton={showEndButton}
        isEnding={isEnding}
        onEndPress={() => setShowEndConfirm(true)}
      />

      {/* Timeline — entries + processing state */}
      {recorder.error ? (
        <View className="flex-1 items-center justify-center px-10">
          <FontAwesome name="exclamation-circle" size={48} color={colors.error} />
          <Text className="text-base text-gray-700 mt-4 text-center">
            {recorder.error}
          </Text>
        </View>
      ) : (
        <Timeline
          sessionId={sessionId!}
          onRetry={upload}
          onStartRecording={handleRecordPress}
          bottomPadding={120}
        />
      )}

      {/* Record button */}
      <RecordButton
        isRecording={recorder.isRecording}
        duration={recorder.duration}
        onPress={handleRecordPress}
        disabled={isProcessing}
        bottom={insets.bottom}
      />

      {/* End Session confirmation */}
      <ConfirmSheet
        visible={showEndConfirm}
        title="End Session?"
        subtitle="You can still edit entries after ending."
        confirmText="End Session"
        onConfirm={handleEndSession}
        onCancel={() => setShowEndConfirm(false)}
        destructive
      />
    </View>
  );
}
