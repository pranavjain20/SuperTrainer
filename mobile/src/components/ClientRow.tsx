import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Pressable, Text, View } from "react-native";

import type { Client } from "@/src/api/types";
import { colors } from "@/src/constants/colors";
import { cardShadow } from "@/src/constants/styles";
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
      className="flex-row items-center mx-4 mb-3 px-5 py-5 bg-white rounded-2xl active:bg-gray-50"
      style={cardShadow}
    >
      {/* Initials circle — large, future profile pic */}
      <View
        className="w-14 h-14 rounded-full items-center justify-center"
        style={{ backgroundColor: color + "20" }}
      >
        <Text className="text-lg font-bold" style={{ color }}>
          {initials}
        </Text>
      </View>

      {/* Name */}
      <Text className="flex-1 text-lg font-bold text-gray-900 ml-4">{client.name}</Text>

      {/* Chevron */}
      <FontAwesome name="chevron-right" size={14} color={colors.chevron} />
    </Pressable>
  );
}
