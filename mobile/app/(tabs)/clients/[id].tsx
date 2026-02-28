import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getSessionEntries } from "@/src/api/entries";
import { classifyWorkout, createSession } from "@/src/api/sessions";
import type { Session, SessionPlan } from "@/src/api/types";
import { EntryCard } from "@/src/components/EntryCard";
import { ErrorState } from "@/src/components/ErrorState";
import { LoadingState } from "@/src/components/LoadingState";
import { colors } from "@/src/constants/colors";
import { cardShadow } from "@/src/constants/styles";
import { useClient, useClientPlans, useClientSessions } from "@/src/hooks/useClient";
import { useEditableEntries } from "@/src/hooks/useEditableEntries";
import { sessionsQueryKey } from "@/src/hooks/useSessions";
import { useRecordingStore } from "@/src/stores/recordingStore";
import { formatMemberSince, formatPlanDate, formatSessionDate, formatTime } from "@/src/utils/dates";
import { getInitials, getInitialsColor } from "@/src/utils/initials";
import { computeSessionStats, formatDurationMinutes, numberExercises } from "@/src/utils/sessions";

// ---------------------------------------------------------------------------
// Tab bar
// ---------------------------------------------------------------------------

const TABS = ["Overview", "Sessions", "Plans"] as const;
type Tab = (typeof TABS)[number];

function ProfileTabBar({
  active,
  onSelect,
}: {
  active: Tab;
  onSelect: (tab: Tab) => void;
}) {
  return (
    <View className="flex-row bg-white border-b border-gray-100 px-4">
      {TABS.map((tab) => {
        const isActive = tab === active;
        return (
          <Pressable
            key={tab}
            onPress={() => onSelect(tab)}
            className="flex-1 items-center py-3.5"
          >
            <Text
              className="text-sm font-bold"
              style={{ color: isActive ? colors.primary : colors.textTertiary }}
            >
              {tab}
            </Text>
            {isActive && (
              <View
                className="absolute bottom-0 left-4 right-4 h-[2.5px] rounded-full"
                style={{ backgroundColor: colors.primary }}
              />
            )}
          </Pressable>
        );
      })}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Helper components
// ---------------------------------------------------------------------------

function GoalPill({ goal }: { goal: string }) {
  return (
    <View
      className="px-4 py-2.5 rounded-full mr-2 mb-2"
      style={{ backgroundColor: colors.primary + "15" }}
    >
      <Text className="text-sm font-bold" style={{ color: colors.primary }}>
        {goal.charAt(0).toUpperCase() + goal.slice(1)}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Expandable session card
// ---------------------------------------------------------------------------

function ExpandableSessionCard({ session }: { session: Session }) {
  const [expanded, setExpanded] = useState(false);

  const entriesQuery = useQuery({
    queryKey: ["entries", "session", session.id],
    queryFn: async () => {
      const res = await getSessionEntries(session.id);
      return res.data;
    },
    enabled: expanded,
    staleTime: 5 * 60 * 1000,
  });

  const classifyQuery = useQuery({
    queryKey: ["sessions", session.id, "classify"],
    queryFn: () => classifyWorkout(session.id),
    enabled: expanded && !!session.ended_at,
    staleTime: Infinity,
  });

  const { setEditingEntry, editModals } = useEditableEntries(session.id);

  const time = formatTime(session.scheduled_for ?? session.started_at);
  const date = formatSessionDate(session.started_at);
  const isCompleted = !!session.ended_at;
  const entries = entriesQuery.data ?? [];
  const stats = entries.length > 0 ? computeSessionStats(entries) : null;
  const workoutType = classifyQuery.data?.workout_type ?? null;

  const hasSummary = isCompleted && (stats || classifyQuery.isLoading);

  return (
    <>
      <View className="bg-white rounded-2xl mx-4 mb-3.5 overflow-hidden" style={cardShadow}>
        {/* Session header — tap to expand */}
        <Pressable
          onPress={() => setExpanded(!expanded)}
          className="flex-row items-center px-5 py-4"
        >
          <View className="flex-1">
            <Text style={{ fontSize: 16, fontWeight: "700", color: colors.text }}>{date}</Text>
            <Text style={{ fontSize: 13, fontWeight: "500", color: colors.textSecondary, marginTop: 2 }}>{time}</Text>
          </View>

          <View className="flex-row items-center">
            {isCompleted && session.duration_minutes != null && (
              <Text style={{ fontSize: 14, fontWeight: "600", color: colors.textSecondary, marginRight: 10 }}>
                {formatDurationMinutes(session.duration_minutes!)}
              </Text>
            )}
            <FontAwesome
              name={expanded ? "chevron-up" : "chevron-down"}
              size={12}
              color={colors.textTertiary}
            />
          </View>
        </Pressable>

        {/* Expanded content */}
        {expanded && (
          <View className="border-t border-gray-100">
            {entriesQuery.isLoading && (
              <View className="py-6 items-center">
                <ActivityIndicator size="small" color={colors.primary} />
              </View>
            )}

            {entriesQuery.isError && (
              <View className="py-4 items-center">
                <Text className="text-sm text-gray-500">Failed to load entries</Text>
              </View>
            )}

            {entriesQuery.data && entriesQuery.data.length === 0 && (
              <View className="py-4 items-center">
                <Text className="text-sm text-gray-500">No entries recorded</Text>
              </View>
            )}

            {entriesQuery.data && entriesQuery.data.length > 0 && (() => {
              const exerciseNumbers = numberExercises(entriesQuery.data);
              return (
                <>
                  {/* ── SUMMARY block ── */}
                  {hasSummary && (
                    <View style={{ backgroundColor: colors.primary + "0C", paddingHorizontal: 20, paddingTop: 14, paddingBottom: 16 }}>
                      {/* Section label */}
                      <Text style={{ fontSize: 13, fontWeight: "900", color: colors.primary, textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 12 }}>
                        Workout Summary
                      </Text>

                      {/* Stat row — type + duration + exercises + sets */}
                      <View className="flex-row">
                        <View style={{ marginRight: 24 }}>
                          <Text style={{ fontSize: 11, fontWeight: "700", color: colors.textTertiary, textTransform: "uppercase", letterSpacing: 0.8 }}>
                            Type
                          </Text>
                          <Text style={{ fontSize: 15, fontWeight: "800", color: colors.text, marginTop: 2 }}>
                            {classifyQuery.isLoading ? "..." : (workoutType ?? "—")}
                          </Text>
                        </View>
                        {session.duration_minutes != null && (
                          <View style={{ marginRight: 24 }}>
                            <Text style={{ fontSize: 11, fontWeight: "700", color: colors.textTertiary, textTransform: "uppercase", letterSpacing: 0.8 }}>
                              Duration
                            </Text>
                            <Text style={{ fontSize: 15, fontWeight: "800", color: colors.text, marginTop: 2 }}>
                              {formatDurationMinutes(session.duration_minutes!)}
                            </Text>
                          </View>
                        )}
                        {stats && (
                          <>
                            <View style={{ marginRight: 24 }}>
                              <Text style={{ fontSize: 11, fontWeight: "700", color: colors.textTertiary, textTransform: "uppercase", letterSpacing: 0.8 }}>
                                Exercises
                              </Text>
                              <Text style={{ fontSize: 15, fontWeight: "800", color: colors.text, marginTop: 2 }}>
                                {stats.exerciseCount}
                              </Text>
                            </View>
                          </>
                        )}
                      </View>
                    </View>
                  )}

                  {/* ── Exercise cards in a bordered container ── */}
                  <View
                    style={{
                      margin: 12,
                      borderWidth: 1,
                      borderColor: colors.borderLight,
                      borderRadius: 12,
                      overflow: "hidden",
                    }}
                  >
                    {entriesQuery.data.map((entry, i) => (
                      <View
                        key={entry.id}
                        style={i > 0 ? { borderTopWidth: 6, borderTopColor: colors.borderLight } : undefined}
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
                </>
              );
            })()}
          </View>
        )}
      </View>

      {editModals}
    </>
  );
}

// ---------------------------------------------------------------------------
// Tab content
// ---------------------------------------------------------------------------

function OverviewTab({ goals, injuryHistory }: { goals: string[] | null; injuryHistory: string | null }) {
  const hasGoals = goals && goals.length > 0;
  const hasInjuries = !!injuryHistory;

  if (!hasGoals && !hasInjuries) {
    return (
      <View className="items-center py-10">
        <FontAwesome name="user-o" size={40} color={colors.textTertiary} />
        <Text className="text-base text-gray-500 mt-3">No details yet</Text>
      </View>
    );
  }

  return (
    <View className="px-4 pt-5 pb-8">
      {hasGoals && (
        <View className="mb-5">
          <Text className="text-base font-bold text-gray-700 mb-3">Goals</Text>
          <View className="flex-row flex-wrap">
            {goals!.map((goal, i) => (
              <GoalPill key={`${goal}-${i}`} goal={goal} />
            ))}
          </View>
        </View>
      )}

      {hasInjuries && (
        <View>
          <Text className="text-base font-bold text-gray-700 mb-3">Injury History</Text>
          <View className="flex-row flex-wrap">
            {injuryHistory!
              .split(/\.\s*/)
              .filter((s) => s.length > 0)
              .map((item, i) => (
                <View
                  key={`injury-${i}`}
                  className="px-4 py-2.5 rounded-full mr-2 mb-2"
                  style={{ backgroundColor: colors.error + "12" }}
                >
                  <Text className="text-sm font-bold" style={{ color: colors.error }}>
                    {(item.replace(/\.$/, "")).charAt(0).toUpperCase() + item.replace(/\.$/, "").slice(1)}
                  </Text>
                </View>
              ))}
          </View>
        </View>
      )}
    </View>
  );
}

function SessionsTab({ sessions }: { sessions: Session[] }) {
  if (sessions.length === 0) {
    return (
      <View className="items-center py-10">
        <FontAwesome name="calendar-o" size={40} color={colors.textTertiary} />
        <Text className="text-base text-gray-500 mt-3">No sessions yet</Text>
      </View>
    );
  }

  return (
    <View className="pt-4 pb-8">
      {sessions.map((session) => (
        <ExpandableSessionCard key={session.id} session={session} />
      ))}
    </View>
  );
}

function PlanCard({ plan }: { plan: SessionPlan }) {
  const lines = plan.plan_text
    .split(/\.\s+/)
    .map((s) => s.replace(/\.$/, "").trim())
    .filter((s) => s.length > 0);

  return (
    <View className="bg-white rounded-2xl mb-3.5 mx-4 overflow-hidden" style={cardShadow}>
      <View className="px-5 py-3 border-b border-gray-100" style={{ backgroundColor: colors.primary + "08" }}>
        <Text className="text-sm font-bold" style={{ color: colors.primary }}>
          {formatPlanDate(plan.planned_for_date)}
        </Text>
      </View>

      {lines.map((line, i) => (
        <View
          key={`line-${i}`}
          className="px-5 py-3.5"
          style={i < lines.length - 1 ? { borderBottomWidth: 1, borderBottomColor: colors.borderLight } : undefined}
        >
          <View className="flex-row">
            <Text className="text-sm font-bold text-gray-400 mr-3 mt-px">{i + 1}</Text>
            <Text className="text-sm text-gray-800 leading-5 flex-1">{line}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

function PlansTab({ plans }: { plans: SessionPlan[] }) {
  if (plans.length === 0) {
    return (
      <View className="items-center py-10">
        <FontAwesome name="clipboard" size={40} color={colors.textTertiary} />
        <Text className="text-base text-gray-500 mt-3">No plans yet</Text>
      </View>
    );
  }

  return (
    <View className="pt-4 pb-8">
      {plans.map((plan) => (
        <PlanCard key={plan.id} plan={plan} />
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export default function ClientDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const { isRecording, stopRecording } = useRecordingStore();

  const clientQuery = useClient(id);
  const sessionsQuery = useClientSessions(id);
  const plansQuery = useClientPlans(id);

  const startSessionMutation = useMutation({
    mutationFn: () =>
      createSession({ client_id: id, started_at: new Date().toISOString() }),
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: sessionsQueryKey.all });
      queryClient.invalidateQueries({ queryKey: ["sessions", "client", id] });
      router.push({ pathname: "/recording/[sessionId]", params: { sessionId: session.id } });
    },
    onError: (error) => {
      Alert.alert("Failed to start session", error.message);
    },
  });

  const handleStartSession = () => {
    if (isRecording) {
      Alert.alert(
        "Recording in progress",
        "You're recording another session. Stop that recording and start a new one?",
        [
          { text: "Cancel", style: "cancel" },
          {
            text: "Stop & Start New",
            style: "destructive",
            onPress: async () => {
              await stopRecording?.();
              startSessionMutation.mutate();
            },
          },
        ],
      );
      return;
    }
    startSessionMutation.mutate();
  };

  const refetch = async () => {
    await Promise.allSettled([
      clientQuery.refetch(),
      sessionsQuery.refetch(),
      plansQuery.refetch(),
    ]);
  };

  if (clientQuery.isLoading || sessionsQuery.isLoading || plansQuery.isLoading) {
    return (
      <View className="flex-1 bg-[#FAFAFA]">
        <LoadingState />
      </View>
    );
  }

  if (clientQuery.isError || sessionsQuery.isError || plansQuery.isError) {
    return (
      <View className="flex-1 bg-[#FAFAFA]">
        <ErrorState
          message={clientQuery.error?.message ?? sessionsQuery.error?.message ?? plansQuery.error?.message ?? "Failed to load client"}
          onRetry={refetch}
        />
      </View>
    );
  }

  const client = clientQuery.data!;
  const sessions = sessionsQuery.data ?? [];
  const plans = plansQuery.data ?? [];

  const initials = getInitials(client.name);
  const initialsColor = getInitialsColor(client.name);

  return (
    <ScrollView
      className="flex-1 bg-[#FAFAFA]"
      refreshControl={<RefreshControl refreshing={false} onRefresh={refetch} />}
    >
      {/* Header */}
      <View className="bg-white pb-6 px-5" style={{ paddingTop: insets.top + 8 }}>
        {/* Back button */}
        <Pressable
          onPress={() => router.back()}
          className="flex-row items-center mb-4 -ml-1"
          hitSlop={{ top: 16, bottom: 16, left: 12, right: 24 }}
        >
          <FontAwesome name="chevron-left" size={20} color={colors.primary} />
          <Text
            className="text-xl font-bold ml-2"
            style={{ color: colors.primary }}
          >
            Clients
          </Text>
        </Pressable>

        <View className="items-center">
          <View
            className="w-28 h-28 rounded-full items-center justify-center"
            style={{ backgroundColor: initialsColor + "30" }}
          >
            <Text className="text-4xl font-bold" style={{ color: initialsColor }}>
              {initials}
            </Text>
          </View>

          <Text className="text-3xl font-bold text-gray-900 mt-5">{client.name}</Text>

          {client.training_start_date && (
            <Text className="text-sm font-medium text-gray-500 mt-1.5">
              {formatMemberSince(client.training_start_date)}
            </Text>
          )}

          {!client.archived && (
            <Pressable
              onPress={handleStartSession}
              disabled={startSessionMutation.isPending}
              className="mt-5 w-full rounded-xl py-3.5 items-center justify-center flex-row"
              style={{
                backgroundColor: startSessionMutation.isPending
                  ? colors.primary + "80"
                  : colors.primary,
              }}
            >
              {startSessionMutation.isPending ? (
                <>
                  <ActivityIndicator size="small" color="#fff" />
                  <Text className="text-base font-bold text-white ml-2">Starting...</Text>
                </>
              ) : (
                <Text className="text-base font-bold text-white">Start Session</Text>
              )}
            </Pressable>
          )}
        </View>
      </View>

      {/* Tab bar */}
      <ProfileTabBar active={activeTab} onSelect={setActiveTab} />

      {/* Tab content */}
      {activeTab === "Overview" && (
        <OverviewTab goals={client.goals} injuryHistory={client.injury_history} />
      )}
      {activeTab === "Sessions" && (
        <SessionsTab sessions={sessions} />
      )}
      {activeTab === "Plans" && (
        <PlansTab plans={plans} />
      )}
    </ScrollView>
  );
}
