import { Stack } from "expo-router";

export default function RecordingLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="[sessionId]" />
    </Stack>
  );
}
