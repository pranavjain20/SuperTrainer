import FontAwesome from "@expo/vector-icons/FontAwesome";
import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { askBrain } from "@/src/api/brain";
import { ThemedText } from "@/src/components/ThemedText";
import suggestions from "@/src/constants/brainSuggestions.json";
import { colors } from "@/src/constants/tokens";

interface Message {
  role: "user" | "assistant";
  text: string;
}

export default function BrainScreen() {
  const insets = useSafeAreaInsets();
  const scrollRef = useRef<ScrollView>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");

  const addMessage = (message: Message) => setMessages((prev) => [...prev, message]);

  const ask = useMutation({
    mutationFn: askBrain,
    onSuccess: (answer) => addMessage({ role: "assistant", text: answer }),
    onError: (err) =>
      addMessage({
        role: "assistant",
        text:
          err instanceof Error
            ? err.message
            : "The Brain couldn't answer that. Try again.",
      }),
  });

  const send = (text: string) => {
    const question = text.trim();
    if (!question || ask.isPending) return;
    addMessage({ role: "user", text: question });
    setDraft("");
    ask.mutate(question);
  };

  const asked = new Set(messages.filter((m) => m.role === "user").map((m) => m.text));
  const remaining = suggestions.filter((q) => !asked.has(q));
  const canSend = draft.trim().length > 0 && !ask.isPending;

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-base"
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View
        className="px-5 pb-4 bg-surface-1 border-b border-border-subtle"
        style={{ paddingTop: insets.top + 12 }}
      >
        <ThemedText variant="display">Brain</ThemedText>
        <ThemedText
          variant="body-medium"
          color={colors.text.secondary}
          style={{ marginTop: 4 }}
        >
          Ask anything about your clients
        </ThemedText>
      </View>

      <ScrollView
        ref={scrollRef}
        className="flex-1"
        contentContainerStyle={{ padding: 16, paddingBottom: 24 }}
        keyboardShouldPersistTaps="handled"
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.length === 0 && (
          <ThemedText
            variant="body"
            color={colors.text.secondary}
            style={{ lineHeight: 22, marginBottom: 16 }}
          >
            Answers come from every session you've logged: sets, weights, notes and
            injuries.
          </ThemedText>
        )}

        {messages.map((message, i) =>
          message.role === "user" ? (
            <View
              key={i}
              className="self-end rounded-2xl px-4 py-3 mb-3"
              style={{ maxWidth: "85%", backgroundColor: colors.blue[500] }}
            >
              <ThemedText variant="body" color={colors.text.inverse}>
                {message.text}
              </ThemedText>
            </View>
          ) : (
            <View
              key={i}
              className="self-start rounded-2xl px-4 py-3 mb-3"
              style={{
                maxWidth: "92%",
                backgroundColor: colors.bg.surface1,
                borderLeftWidth: 3,
                borderLeftColor: colors.ai[500],
              }}
            >
              <ThemedText
                variant="body"
                color={colors.text.primary}
                style={{ lineHeight: 22 }}
              >
                {message.text}
              </ThemedText>
            </View>
          ),
        )}

        {ask.isPending && (
          <View className="self-start flex-row items-center px-4 py-3 mb-3">
            <ActivityIndicator size="small" color={colors.ai[400]} />
            <ThemedText
              variant="body-small"
              color={colors.text.secondary}
              style={{ marginLeft: 8 }}
            >
              Thinking…
            </ThemedText>
          </View>
        )}

        {remaining.length > 0 && !ask.isPending && (
          <View style={{ marginTop: messages.length ? 8 : 0 }}>
            <ThemedText
              variant="caption"
              color={colors.text.tertiary}
              style={{ marginBottom: 8 }}
            >
              Try asking
            </ThemedText>
            {remaining.map((question) => (
              <Pressable
                key={question}
                onPress={() => send(question)}
                className="flex-row items-center rounded-xl px-4 py-3 mb-2"
                style={{ backgroundColor: colors.ai.alpha10 }}
              >
                <FontAwesome name="bolt" size={13} color={colors.ai[400]} />
                <ThemedText
                  variant="body"
                  color={colors.text.primary}
                  style={{ marginLeft: 10, flex: 1 }}
                >
                  {question}
                </ThemedText>
              </Pressable>
            ))}
          </View>
        )}
      </ScrollView>

      <View
        className="flex-row items-center px-4 py-3 border-t border-border-subtle bg-surface-1"
        style={{ gap: 10 }}
      >
        <TextInput
          className="flex-1 rounded-xl px-4 py-3"
          style={{
            backgroundColor: colors.bg.surface2,
            fontSize: 16,
            fontFamily: "Inter-Regular",
            color: colors.text.primary,
          }}
          value={draft}
          onChangeText={setDraft}
          onSubmitEditing={() => send(draft)}
          placeholder="Ask about a client…"
          placeholderTextColor={colors.text.tertiary}
          returnKeyType="send"
          maxLength={500}
        />
        <Pressable
          onPress={() => send(draft)}
          disabled={!canSend}
          className="w-11 h-11 rounded-full items-center justify-center"
          style={{ backgroundColor: colors.blue[500], opacity: canSend ? 1 : 0.4 }}
        >
          <FontAwesome name="arrow-up" size={18} color={colors.text.inverse} />
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}
