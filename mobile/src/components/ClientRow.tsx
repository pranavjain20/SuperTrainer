import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Pressable, View } from "react-native";

import type { Client } from "@/src/api/types";
import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";
import { cardBorder } from "@/src/constants/styles";
import { getInitials, getInitialsColor } from "@/src/utils/initials";

interface ClientRowProps {
  client: Client;
  onPress: (client: Client) => void;
}

export function ClientRow({ client, onPress }: ClientRowProps) {
  const initials = getInitials(client.name);
  const color = getInitialsColor(client.name);

  return (
    <Pressable
      onPress={() => onPress(client)}
      className="flex-row items-center mx-4 mb-3 px-5 py-5 rounded-xl"
      style={{ backgroundColor: colors.bg.surface1, ...cardBorder }}
    >
      {/* Initials circle — large, future profile pic */}
      <View
        className="w-14 h-14 rounded-full items-center justify-center"
        style={{ backgroundColor: color + "4D" }}
      >
        <ThemedText variant="title-3" color={color}>
          {initials}
        </ThemedText>
      </View>

      {/* Name */}
      <ThemedText variant="title-3" style={{ flex: 1, marginLeft: 16 }}>
        {client.name}
      </ThemedText>

      {/* Chevron */}
      <FontAwesome name="chevron-right" size={14} color={colors.text.tertiary} />
    </Pressable>
  );
}
