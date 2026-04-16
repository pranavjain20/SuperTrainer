import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { createSession } from "@/src/api/sessions";
import type { Session, SessionEntry, SessionPlan, WeightUnit } from "@/src/api/types";
import { ErrorState } from "@/src/components/ErrorState";
import { ExpandableSessionCard } from "@/src/components/ExpandableSessionCard";
import { LoadingState } from "@/src/components/LoadingState";
import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";
import { cardBorder } from "@/src/constants/styles";
import { groupEntriesBySession, useClient, useClientEntries, useClientPlans, useClientSessions } from "@/src/hooks/useClient";
import { sessionsQueryKey } from "@/src/hooks/useSessions";
import { useRecordingStore } from "@/src/stores/recordingStore";
import { formatMemberSince, formatPlanDate } from "@/src/utils/dates";
import { getInitials, getInitialsColor } from "@/src/utils/initials";

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
    <View
      className="flex-row px-4"
      style={{ backgroundColor: colors.bg.surface1, borderBottomWidth: 1, borderBottomColor: colors.border.subtle }}
    >
      {TABS.map((tab) => {
        const isActive = tab === active;
        return (
          <Pressable
            key={tab}
            onPress={() => onSelect(tab)}
            className="flex-1 items-center py-3.5"
          >
            <ThemedText
              variant="body-medium"
              color={isActive ? colors.blue[500] : colors.text.tertiary}
              style={{ fontSize: 14 }}
            >
              {tab}
            </ThemedText>
            {isActive && (
              <View
                className="absolute bottom-0 left-4 right-4 h-[2.5px] rounded-full"
                style={{ backgroundColor: colors.blue[500] }}
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
      style={{ backgroundColor: colors.blue.alpha12 }}
    >
      <ThemedText variant="body-small" color={colors.blue[500]} style={{ fontFamily: "Inter-SemiBold" }}>
        {goal.charAt(0).toUpperCase() + goal.slice(1)}
      </ThemedText>
    </View>
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
        <FontAwesome name="user-o" size={40} color={colors.text.tertiary} />
        <ThemedText variant="body" color={colors.text.secondary} style={{ marginTop: 12 }}>No details yet</ThemedText>
      </View>
    );
  }

  return (
    <View className="px-4 pt-5 pb-8">
      {hasGoals && (
        <View className="mb-5">
          <ThemedText variant="title-3" color={colors.text.secondary} style={{ marginBottom: 12 }}>Goals</ThemedText>
          <View className="flex-row flex-wrap">
            {goals!.map((goal, i) => (
              <GoalPill key={`${goal}-${i}`} goal={goal} />
            ))}
          </View>
        </View>
      )}

      {hasInjuries && (
        <View>
          <ThemedText variant="title-3" color={colors.text.secondary} style={{ marginBottom: 12 }}>Injury History</ThemedText>
          <View className="flex-row flex-wrap">
            {injuryHistory!
              .split(/\.\s*/)
              .filter((s) => s.length > 0)
              .map((item, i) => (
                <View
                  key={`injury-${i}`}
                  className="px-4 py-2.5 rounded-full mr-2 mb-2"
                  style={{ backgroundColor: colors.red.alpha12 }}
                >
                  <ThemedText variant="body-small" color={colors.red[500]} style={{ fontFamily: "Inter-SemiBold" }}>
                    {(item.replace(/\.$/, "")).charAt(0).toUpperCase() + item.replace(/\.$/, "").slice(1)}
                  </ThemedText>
                </View>
              ))}
          </View>
        </View>
      )}
    </View>
  );
}

function SessionsTab({
  sessions,
  entriesBySession,
  weightUnit,
}: {
  sessions: Session[];
  entriesBySession: Map<string, SessionEntry[]>;
  weightUnit: WeightUnit;
}) {
  if (sessions.length === 0) {
    return (
      <View className="items-center py-10">
        <FontAwesome name="calendar-o" size={40} color={colors.text.tertiary} />
        <ThemedText variant="body" color={colors.text.secondary} style={{ marginTop: 12 }}>No sessions yet</ThemedText>
      </View>
    );
  }

  return (
    <View className="pt-4 pb-8">
      {sessions.map((session) => (
        <ExpandableSessionCard
          key={session.id}
          session={session}
          compactEntries={entriesBySession.get(session.id)}
          weightUnit={weightUnit}
        />
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
    <View
      className="rounded-xl mb-3.5 mx-4 overflow-hidden"
      style={{ backgroundColor: colors.bg.surface1, ...cardBorder }}
    >
      <View className="px-5 py-3" style={{ backgroundColor: colors.blue.alpha12, borderBottomWidth: 1, borderBottomColor: colors.border.subtle }}>
        <ThemedText variant="body-small" color={colors.blue[500]} style={{ fontFamily: "Inter-SemiBold" }}>
          {formatPlanDate(plan.planned_for_date)}
        </ThemedText>
      </View>

      {lines.map((line, i) => (
        <View
          key={`line-${i}`}
          className="px-5 py-3.5"
          style={i < lines.length - 1 ? { borderBottomWidth: 1, borderBottomColor: colors.border.subtle } : undefined}
        >
          <View className="flex-row">
            <ThemedText variant="data" color={colors.text.tertiary} style={{ fontSize: 14, marginRight: 12, marginTop: 1 }}>{i + 1}</ThemedText>
            <ThemedText variant="body-small" style={{ flex: 1, lineHeight: 20 }}>{line}</ThemedText>
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
        <FontAwesome name="clipboard" size={40} color={colors.text.tertiary} />
        <ThemedText variant="body" color={colors.text.secondary} style={{ marginTop: 12 }}>No plans yet</ThemedText>
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
  const entriesQuery = useClientEntries(id);

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

  const entriesBySession = useMemo(
    () => groupEntriesBySession(entriesQuery.data ?? []),
    [entriesQuery.data],
  );

  const refetch = async () => {
    await Promise.allSettled([
      clientQuery.refetch(),
      sessionsQuery.refetch(),
      plansQuery.refetch(),
      entriesQuery.refetch(),
    ]);
  };

  if (clientQuery.isLoading || sessionsQuery.isLoading || plansQuery.isLoading) {
    return (
      <View className="flex-1 bg-base">
        <LoadingState />
      </View>
    );
  }

  if (clientQuery.isError || sessionsQuery.isError || plansQuery.isError) {
    return (
      <View className="flex-1 bg-base">
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
      className="flex-1 bg-base"
      refreshControl={<RefreshControl refreshing={false} onRefresh={refetch} />}
    >
      {/* Header */}
      <View
        className="pb-6 px-5"
        style={{ backgroundColor: colors.bg.surface1, paddingTop: insets.top + 8 }}
      >
        {/* Back button */}
        <Pressable
          onPress={() => router.back()}
          className="flex-row items-center mb-4 -ml-1"
          hitSlop={{ top: 16, bottom: 16, left: 12, right: 24 }}
        >
          <FontAwesome name="chevron-left" size={20} color={colors.blue[500]} />
          <ThemedText variant="title-3" color={colors.blue[500]} style={{ marginLeft: 8 }}>
            Clients
          </ThemedText>
        </Pressable>

        {/* Compact horizontal header — avatar left, name+meta right */}
        <View className="flex-row items-center">
          <View
            className="w-16 h-16 rounded-full items-center justify-center"
            style={{ backgroundColor: initialsColor + "4D" }}
          >
            <ThemedText variant="title-1" color={initialsColor} style={{ fontSize: 22 }}>
              {initials}
            </ThemedText>
          </View>

          <View className="flex-1 ml-4">
            <ThemedText variant="title-1">{client.name}</ThemedText>
            {client.training_start_date && (
              <ThemedText variant="body-small" color={colors.text.secondary} style={{ marginTop: 2 }}>
                {formatMemberSince(client.training_start_date)}
              </ThemedText>
            )}
          </View>
        </View>

        {!client.archived && (
          <Pressable
            onPress={handleStartSession}
            disabled={startSessionMutation.isPending}
            className="mt-5 w-full rounded-xl py-3.5 items-center justify-center flex-row"
            style={{
              backgroundColor: startSessionMutation.isPending
                ? colors.blue[500] + "80"
                : colors.blue[500],
            }}
          >
            {startSessionMutation.isPending ? (
              <>
                <ActivityIndicator size="small" color={colors.text.inverse} />
                <ThemedText variant="body-medium" color={colors.text.inverse} style={{ marginLeft: 8 }}>Starting...</ThemedText>
              </>
            ) : (
              <ThemedText variant="body-medium" color={colors.text.inverse}>Start Session</ThemedText>
            )}
          </Pressable>
        )}
      </View>

      {/* Tab bar */}
      <ProfileTabBar active={activeTab} onSelect={setActiveTab} />

      {/* Tab content */}
      {activeTab === "Overview" && (
        <OverviewTab goals={client.goals} injuryHistory={client.injury_history} />
      )}
      {activeTab === "Sessions" && (
        <SessionsTab
          sessions={sessions}
          entriesBySession={entriesBySession}
          weightUnit={client.preferred_weight_unit ?? "kg"}
        />
      )}
      {activeTab === "Plans" && (
        <PlansTab plans={plans} />
      )}
    </ScrollView>
  );
}
