/**
 * Demo-only layers drawn over the app.
 *
 * - Caption: what the playing sample clip says, so the demo reads even with
 *   sound off, and a prompt to tap stop once the clip ends.
 * - Alerts: react-native-web's Alert.alert does nothing, which would silently
 *   swallow the app's confirmations and error messages. In the demo, alerts
 *   render here instead, in the app's own style.
 */

import { Alert, type AlertButton, Pressable, View } from "react-native";
import { create } from "zustand";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

import { IS_DEMO } from "./config";
import { useDemoCaption } from "./useDemoRecorder";

interface PendingAlert {
  title: string;
  message?: string;
  buttons: AlertButton[];
}

const useDemoAlert = create<{ alert: PendingAlert | null }>(() => ({ alert: null }));

if (IS_DEMO) {
  Alert.alert = (title, message, buttons) => {
    useDemoAlert.setState({
      alert: { title, message, buttons: buttons?.length ? buttons : [{ text: "OK" }] },
    });
  };
}

function Caption() {
  const { text, done } = useDemoCaption();
  if (!text) return null;

  return (
    <View
      pointerEvents="none"
      style={{
        position: "absolute",
        left: 16,
        right: 16,
        bottom: 150,
        alignItems: "center",
      }}
    >
      <View
        style={{
          maxWidth: 340,
          paddingVertical: 12,
          paddingHorizontal: 16,
          borderRadius: 14,
          backgroundColor: colors.bg.surface1,
          borderWidth: 1,
          borderColor: colors.border.subtle,
        }}
      >
        <ThemedText variant="caption" color={colors.text.tertiary}>
          Sample clip
        </ThemedText>
        <ThemedText
          variant="body"
          color={colors.text.primary}
          style={{ marginTop: 4, lineHeight: 22 }}
        >
          “{text}”
        </ThemedText>
        {done && (
          <ThemedText
            variant="body-medium"
            color={colors.blue[500]}
            style={{ marginTop: 8 }}
          >
            Tap stop to send it.
          </ThemedText>
        )}
      </View>
    </View>
  );
}

function AlertDialog() {
  const alert = useDemoAlert((s) => s.alert);
  if (!alert) return null;

  const choose = (button: AlertButton) => {
    useDemoAlert.setState({ alert: null });
    button.onPress?.();
  };
  const cancel = alert.buttons.find((b) => b.style === "cancel");

  return (
    <Pressable
      onPress={() => cancel && choose(cancel)}
      style={{
        position: "absolute",
        inset: 0,
        alignItems: "center",
        justifyContent: "center",
        padding: 32,
        backgroundColor: "rgba(0, 0, 0, 0.6)",
      }}
    >
      <Pressable
        style={{
          width: "100%",
          maxWidth: 320,
          borderRadius: 18,
          padding: 20,
          backgroundColor: colors.bg.surface1,
        }}
      >
        <ThemedText variant="title-2">{alert.title}</ThemedText>
        {alert.message && (
          <ThemedText
            variant="body"
            color={colors.text.secondary}
            style={{ marginTop: 6, lineHeight: 22 }}
          >
            {alert.message}
          </ThemedText>
        )}
        <View style={{ flexDirection: "row", gap: 10, marginTop: 20 }}>
          {alert.buttons.map((button) => (
            <Pressable
              key={button.text}
              onPress={() => choose(button)}
              style={{
                flex: 1,
                paddingVertical: 12,
                borderRadius: 12,
                alignItems: "center",
                backgroundColor:
                  button.style === "destructive"
                    ? colors.red[500]
                    : button.style === "cancel"
                      ? colors.bg.surface2
                      : colors.blue[500],
              }}
            >
              <ThemedText
                variant="body-medium"
                color={
                  button.style === "cancel" ? colors.text.secondary : colors.text.inverse
                }
              >
                {button.text}
              </ThemedText>
            </Pressable>
          ))}
        </View>
      </Pressable>
    </Pressable>
  );
}

export function DemoOverlays() {
  return (
    <>
      <Caption />
      <AlertDialog />
    </>
  );
}
