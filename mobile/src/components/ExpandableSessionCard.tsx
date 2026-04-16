import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ActivityIndicator, Pressable, View } from "react-native";

import { getSessionEntries } from "@/src/api/entries";
import type { Session, SessionEntry, WeightUnit } from "@/src/api/types";
import { EntryCard } from "@/src/components/EntryCard";
import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";
import { cardBorder } from "@/src/constants/styles";
import { useEditableEntries } from "@/src/hooks/useEditableEntries";
import { formatSessionDate, formatTime } from "@/src/utils/dates";
import { classifyWorkoutFromEntries, formatDurationMinutes, numberExercises } from "@/src/utils/sessions";
import { formatCompactExerciseParts } from "@/src/utils/sets";

type CardView = "collapsed" | "summary" | "detail";

interface ExpandableSessionCardProps {
  session: Session;
  compactEntries?: SessionEntry[];
  weightUnit: WeightUnit;
  /** Override the initial view state. Defaults to "collapsed". */
  defaultView?: CardView;
  /** When true, collapsed state shows workout type + exercise names for quick identification. */
  showPreview?: boolean;
  /** When true, only allows collapsed ↔ summary toggle. No detail view or "View full workout". */
  summaryOnly?: boolean;
}

export function ExpandableSessionCard({
  session,
  compactEntries,
  weightUnit,
  defaultView = "collapsed",
  showPreview = false,
  summaryOnly = false,
}: ExpandableSessionCardProps) {
  const [view, setView] = useState<CardView>(defaultView);

  const entriesQuery = useQuery({
    queryKey: ["entries", "session", session.id],
    queryFn: async () => {
      const res = await getSessionEntries(session.id);
      return res.data;
    },
    enabled: view === "detail",
    staleTime: 5 * 60 * 1000,
  });

  const { setEditingEntry, editModals } = useEditableEntries(session.id);

  const time = formatTime(session.scheduled_for ?? session.started_at);
  const date = formatSessionDate(session.started_at);
  const isCompleted = !!session.ended_at;

  const exerciseEntries = compactEntries?.filter((e) => e.entry_type === "exercise_card") ?? [];
  const hasCompactData = isCompleted && exerciseEntries.length > 0;

  const handleHeaderTap = () => {
    if (view === "collapsed") {
      setView(hasCompactData ? "summary" : "detail");
    } else {
      setView("collapsed");
    }
  };

  return (
    <>
      <View
        className="rounded-xl mx-4 mb-2.5 overflow-hidden"
        style={{
          backgroundColor: colors.bg.surface1,
          ...cardBorder,
          ...(view !== "collapsed" ? { borderLeftWidth: 3, borderLeftColor: colors.blue[500] } : {}),
        }}
      >
        {/* Session header — tap to toggle */}
        <Pressable onPress={handleHeaderTap} className="flex-row items-center px-5" style={{ paddingTop: 12, paddingBottom: showPreview ? 6 : 12 }}>
          <View className="flex-1">
            <ThemedText variant="title-3">{date}</ThemedText>
            {!showPreview && (
              <ThemedText variant="body-small" color={colors.text.secondary} style={{ marginTop: 2 }}>{time}</ThemedText>
            )}
          </View>
          <View className="flex-row items-center">
            {isCompleted && session.duration_minutes != null && (
              <ThemedText variant="data" color={colors.text.secondary} style={{ fontSize: 14, marginRight: 10 }}>
                {formatDurationMinutes(session.duration_minutes!)}
              </ThemedText>
            )}
            <FontAwesome
              name={view === "collapsed" ? "chevron-down" : "chevron-up"}
              size={12}
              color={colors.text.tertiary}
            />
          </View>
        </Pressable>

        {/* ── Collapsed preview: workout type + exercise names ── */}
        {view === "collapsed" && showPreview && hasCompactData && (
          <View className="px-5" style={{ paddingBottom: 12 }}>
            <ThemedText variant="body-small" color={colors.blue[400]} style={{ fontFamily: "Inter-Bold", marginBottom: 4, letterSpacing: 0.5 }}>
              {classifyWorkoutFromEntries(exerciseEntries).toUpperCase()}
            </ThemedText>
            <ThemedText variant="body" color={colors.text.primary} numberOfLines={2} style={{ fontFamily: "Inter-Medium", lineHeight: 22 }}>
              {exerciseEntries
                .map((e) => {
                  const name = e.exercise_name ?? e.exercise_canonical ?? "Unknown";
                  return name.charAt(0).toUpperCase() + name.slice(1);
                })
                .join("  ·  ")}
            </ThemedText>
          </View>
        )}

        {/* ── Summary view ── */}
        {view === "summary" && hasCompactData && (
          <View style={{ paddingHorizontal: 20, paddingBottom: 16 }}>
            <ThemedText variant="title-1" color={colors.blue[400]} style={{ fontFamily: "Inter-Bold", marginBottom: 8 }}>
              {classifyWorkoutFromEntries(exerciseEntries)}
            </ThemedText>
            {exerciseEntries.map((entry, i) => {
              const { name, sets } = formatCompactExerciseParts(entry, weightUnit);
              return (
                <View key={entry.id} style={{ marginBottom: i < exerciseEntries.length - 1 ? 6 : 0 }}>
                  <ThemedText variant="body" style={{ fontFamily: "Inter-SemiBold" }}>
                    {name}
                  </ThemedText>
                  {sets.length > 0 && (
                    <ThemedText variant="data" color={colors.text.secondary} style={{ marginTop: 2 }}>
                      {sets}
                    </ThemedText>
                  )}
                </View>
              );
            })}

            {!summaryOnly && (
              <Pressable
                onPress={() => setView("detail")}
                className="flex-row items-center justify-center self-end rounded-full"
                style={{ marginTop: 12, backgroundColor: colors.blue.alpha12, paddingHorizontal: 16, paddingVertical: 8 }}
              >
                <ThemedText variant="body-medium" color={colors.blue[500]} style={{ fontFamily: "Inter-Bold" }}>
                  View full workout
                </ThemedText>
                <FontAwesome name="angle-right" size={16} color={colors.blue[500]} style={{ marginLeft: 6 }} />
              </Pressable>
            )}
          </View>
        )}

        {/* ── Detail view — full entry cards ── */}
        {view === "detail" && (
          <View style={{ borderTopWidth: 1, borderTopColor: colors.border.subtle }}>
            {entriesQuery.isLoading && (
              <View className="py-6 items-center">
                <ActivityIndicator size="small" color={colors.blue[500]} />
              </View>
            )}

            {entriesQuery.isError && (
              <View className="py-4 items-center">
                <ThemedText variant="body-small" color={colors.text.secondary}>Failed to load entries</ThemedText>
              </View>
            )}

            {entriesQuery.data && entriesQuery.data.length === 0 && (
              <View className="py-4 items-center">
                <ThemedText variant="body-small" color={colors.text.secondary}>No entries recorded</ThemedText>
              </View>
            )}

            {entriesQuery.data && entriesQuery.data.length > 0 && (() => {
              const exerciseNumbers = numberExercises(entriesQuery.data);
              return (
                <>
                  {/* ── Exercise cards in a bordered container ── */}
                  <View
                    style={{
                      margin: 12,
                      borderWidth: 1,
                      borderColor: colors.border.subtle,
                      borderRadius: 12,
                      overflow: "hidden",
                    }}
                  >
                    {entriesQuery.data.map((entry, i) => (
                      <View
                        key={entry.id}
                        style={i > 0 ? { borderTopWidth: 1, borderTopColor: colors.border.subtle } : undefined}
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
