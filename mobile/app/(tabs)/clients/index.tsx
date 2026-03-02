import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { SectionList, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import type { Client } from "@/src/api/types";
import { ClientRow } from "@/src/components/ClientRow";
import { EmptyState } from "@/src/components/EmptyState";
import { ErrorState } from "@/src/components/ErrorState";
import { LoadingState } from "@/src/components/LoadingState";
import { ThemedText } from "@/src/components/ThemedText";
import { useClients } from "@/src/hooks/useClients";
import { colors } from "@/src/constants/tokens";

interface ClientSection {
  title: string;
  data: Client[];
}

/**
 * Group clients by first letter of their name for the section list.
 */
function groupByFirstLetter(clients: Client[]): ClientSection[] {
  const groups = new Map<string, Client[]>();
  for (const client of clients) {
    const letter = client.name[0].toUpperCase();
    const existing = groups.get(letter);
    if (existing) {
      existing.push(client);
    } else {
      groups.set(letter, [client]);
    }
  }

  return Array.from(groups.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([title, data]) => ({ title, data }));
}

export default function ClientsScreen() {
  const router = useRouter();
  const { data: clients, isLoading, isError, error, refetch } = useClients();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!clients) return [];
    if (!search.trim()) return clients;
    const q = search.toLowerCase().trim();
    return clients.filter((c) => c.name.toLowerCase().includes(q));
  }, [clients, search]);

  const sections = useMemo(() => groupByFirstLetter(filtered), [filtered]);

  const insets = useSafeAreaInsets();

  const handlePress = useCallback(
    (client: Client) => {
      router.push({
        pathname: "/clients/[id]",
        params: { id: client.id },
      });
    },
    [router],
  );

  if (isLoading) {
    return (
      <View className="flex-1 bg-base">
        <LoadingState />
      </View>
    );
  }

  if (isError) {
    return (
      <View className="flex-1 bg-base">
        <ErrorState
          message={error?.message ?? "Failed to load clients"}
          onRetry={refetch}
        />
      </View>
    );
  }

  const hasClients = clients && clients.length > 0;
  const hasResults = filtered.length > 0;

  return (
    <View className="flex-1 bg-base">
      {/* Search bar + count */}
      {hasClients && (
        <View
          className="px-5 pb-3 bg-surface-1 border-b border-border-subtle"
          style={{ paddingTop: insets.top + 12 }}
        >
          <ThemedText variant="display">Clients</ThemedText>
          <ThemedText
            variant="body-medium"
            color={colors.text.secondary}
            style={{ marginTop: 4, marginBottom: 12 }}
          >
            {filtered.length} active {filtered.length === 1 ? "client" : "clients"}
          </ThemedText>
          <View className="flex-row items-center bg-surface-2 rounded-lg px-4 py-3">
            <FontAwesome name="search" size={16} color={colors.text.tertiary} />
            <TextInput
              className="flex-1 ml-3 text-base"
              style={{ color: colors.text.primary, fontFamily: "Inter-Regular" }}
              placeholder="Search clients..."
              placeholderTextColor={colors.text.tertiary}
              value={search}
              onChangeText={setSearch}
              autoCapitalize="none"
              autoCorrect={false}
            />
            {search.length > 0 && (
              <FontAwesome
                name="times-circle"
                size={18}
                color={colors.text.tertiary}
                onPress={() => setSearch("")}
              />
            )}
          </View>
        </View>
      )}

      <SectionList
        sections={sections}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <ClientRow client={item} onPress={handlePress} />}
        renderSectionHeader={({ section }) => (
          <View className="px-5 pt-4 pb-1 bg-base">
            <ThemedText variant="caption" color={colors.text.tertiary}>
              {section.title}
            </ThemedText>
          </View>
        )}
        contentContainerStyle={
          !hasClients || (!hasResults && search) ? { flex: 1 } : undefined
        }
        ListEmptyComponent={
          !hasClients ? (
            <EmptyState
              icon="users"
              title="No clients yet"
              subtitle="Add your first client to get started"
            />
          ) : !hasResults ? (
            <EmptyState
              icon="search"
              title="No results"
              subtitle={`No clients matching "${search}"`}
            />
          ) : null
        }
        stickySectionHeadersEnabled
        refreshing={false}
        onRefresh={refetch}
      />
    </View>
  );
}
