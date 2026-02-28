/**
 * Shared session list used by both Home (Today) and Sessions tabs.
 * Each tab passes its own title and empty-state subtitle.
 */

import { useRouter } from "expo-router";
import { FlatList, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { EmptyState } from "@/src/components/EmptyState";
import { ErrorState } from "@/src/components/ErrorState";
import { LoadingState } from "@/src/components/LoadingState";
import { SessionRow } from "@/src/components/SessionRow";
import type { SessionWithClient } from "@/src/hooks/useSessions";
import { useTodaySessions } from "@/src/hooks/useSessions";
import { formatDayHeader } from "@/src/utils/dates";

interface SessionListScreenProps {
  title: string;
  emptySubtitle: string;
}

export function SessionListScreen({ title, emptySubtitle }: SessionListScreenProps) {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data: sessions, isLoading, isError, error, refetch } = useTodaySessions();
  const today = formatDayHeader(new Date());

  const handleSessionPress = (session: SessionWithClient) => {
    router.push({ pathname: "/recording/[sessionId]", params: { sessionId: session.id } });
  };

  if (isLoading) {
    return (
      <View className="flex-1 bg-[#FAFAFA]">
        <LoadingState />
      </View>
    );
  }

  if (isError) {
    return (
      <View className="flex-1 bg-[#FAFAFA]">
        <ErrorState
          message={error?.message ?? "Failed to load sessions"}
          onRetry={refetch}
        />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-[#FAFAFA]">
      <FlatList
        data={sessions}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <SessionRow session={item} onPress={handleSessionPress} />
        )}
        contentContainerStyle={
          sessions.length === 0 ? { flex: 1 } : { paddingBottom: 16 }
        }
        ListHeaderComponent={
          <View className="px-5 pb-4 bg-white" style={{ paddingTop: insets.top + 12 }}>
            <Text className="text-3xl font-bold text-gray-900">{title}</Text>
            <Text className="text-lg font-semibold text-gray-500 mt-1">{today}</Text>
          </View>
        }
        ListEmptyComponent={
          <EmptyState
            icon="calendar-o"
            title="No sessions today"
            subtitle={emptySubtitle}
          />
        }
        refreshing={false}
        onRefresh={refetch}
      />
    </View>
  );
}
