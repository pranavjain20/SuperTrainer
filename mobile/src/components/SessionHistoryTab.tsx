/**
 * Session history view for the recording screen.
 *
 * Shows the client's recent past sessions (excluding the current one) as
 * expandable cards with compact exercise format. The most recent sessions
 * default to summary view so the trainer can immediately see numbers.
 */

import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useMemo } from "react";
import { ActivityIndicator, ScrollView, View } from "react-native";

import type { WeightUnit } from "@/src/api/types";
import { EmptyState } from "@/src/components/EmptyState";
import { ExpandableSessionCard } from "@/src/components/ExpandableSessionCard";
import { groupEntriesBySession, useClientEntries, useClientSessions } from "@/src/hooks/useClient";


interface SessionHistoryTabProps {
  clientId: string;
  currentSessionId: string;
  weightUnit: WeightUnit;
  bottomPadding?: number;
}

export function SessionHistoryTab({
  clientId,
  currentSessionId,
  weightUnit,
  bottomPadding = 120,
}: SessionHistoryTabProps) {
  const sessionsQuery = useClientSessions(clientId);
  const entriesQuery = useClientEntries(clientId);

  const entriesBySession = useMemo(
    () => groupEntriesBySession(entriesQuery.data ?? []),
    [entriesQuery.data],
  );

  const pastSessions = useMemo(() => {
    const sessions = (sessionsQuery.data ?? []).filter((s) => s.id !== currentSessionId);
    // Only show sessions that have exercise entries — empty sessions aren't useful for history
    return sessions.filter((s) => {
      const entries = entriesBySession.get(s.id);
      return entries?.some((e) => e.entry_type === "exercise_card");
    });
  }, [sessionsQuery.data, currentSessionId, entriesBySession]);

  if (sessionsQuery.isLoading || entriesQuery.isLoading) {
    return (
      <View className="flex-1 items-center justify-center">
        <ActivityIndicator size="small" />
      </View>
    );
  }

  if (pastSessions.length === 0) {
    return (
      <EmptyState
        icon="calendar-o"
        title="No past sessions"
        subtitle="History will appear here after the first session"
      />
    );
  }

  return (
    <ScrollView
      className="flex-1"
      contentContainerStyle={{ paddingTop: 16, paddingBottom: bottomPadding + 40 }}
    >
      {pastSessions.map((session, i) => (
        <ExpandableSessionCard
          key={session.id}
          session={session}
          compactEntries={entriesBySession.get(session.id)}
          weightUnit={weightUnit}
          showPreview
          summaryOnly
        />
      ))}
    </ScrollView>
  );
}
