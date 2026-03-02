import FontAwesome from "@expo/vector-icons/FontAwesome";
import { Tabs, useRouter } from "expo-router";
import { ComponentProps } from "react";
import { Alert, View } from "react-native";

import { ActiveSessionBanner } from "@/src/components/ActiveSessionBanner";
import { colors } from "@/src/constants/tokens";
import { useRecordingStore } from "@/src/stores/recordingStore";

function TabIcon(props: {
  name: ComponentProps<typeof FontAwesome>["name"];
  color: string;
}) {
  return <FontAwesome size={24} style={{ marginBottom: -2 }} {...props} />;
}

// Route paths for each tab name
const TAB_ROUTES: Record<string, string> = {
  index: "/",
  clients: "/clients",
  brain: "/brain",
  session: "/session",
};

export default function TabLayout() {
  const isRecording = useRecordingStore((s) => s.isRecording);
  const stopRecording = useRecordingStore((s) => s.stopRecording);
  const router = useRouter();

  // Build listeners that guard non-session tabs when recording
  const recordingGuard = (tabName: string) => ({
    tabPress: (e: { preventDefault: () => void }) => {
      if (!isRecording) return;
      // Recording is at root level now — all tabs get the guard

      e.preventDefault();

      Alert.alert(
        "Recording in progress",
        "You have a recording running. Are you sure you want to navigate away?",
        [
          { text: "Keep Recording", style: "cancel" },
          {
            text: "Stop & Leave",
            style: "destructive",
            onPress: async () => {
              if (stopRecording) await stopRecording();
              router.navigate(TAB_ROUTES[tabName] as any);
            },
          },
        ],
      );
    },
  });

  return (
    <View style={{ flex: 1 }}>
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: colors.blue[500],
          tabBarInactiveTintColor: colors.text.tertiary,
          tabBarStyle: {
            backgroundColor: colors.bg.surface1,
            borderTopColor: colors.border.subtle,
            borderTopWidth: 1,
          },
          headerStyle: {
            backgroundColor: colors.bg.surface1,
          },
          headerTintColor: colors.text.primary,
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: "Home",
            headerShown: false,
            tabBarIcon: ({ color }) => <TabIcon name="home" color={color} />,
          }}
          listeners={recordingGuard("index")}
        />
        <Tabs.Screen
          name="clients"
          options={{
            title: "Clients",
            headerShown: false,
            tabBarIcon: ({ color }) => <TabIcon name="users" color={color} />,
          }}
          listeners={recordingGuard("clients")}
        />
        <Tabs.Screen
          name="brain"
          options={{
            title: "Brain",
            headerShown: false,
            tabBarIcon: ({ color }) => <TabIcon name="bolt" color={color} />,
          }}
          listeners={recordingGuard("brain")}
        />
        <Tabs.Screen
          name="session"
          options={{
            title: "Sessions",
            headerShown: false,
            tabBarIcon: ({ color }) => <TabIcon name="microphone" color={color} />,
          }}
          listeners={recordingGuard("session")}
        />
      </Tabs>
      <ActiveSessionBanner />
    </View>
  );
}
