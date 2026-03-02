/**
 * Bottom-sheet time picker for "forgotten" sessions.
 *
 * When a session has been running longer than the threshold (2h prod / 30s dev),
 * this sheet asks the trainer when the session actually ended instead of
 * silently stamping now().
 */

import { useState } from "react";
import { Modal, Platform, Pressable, View } from "react-native";
import DateTimePicker, {
  type DateTimePickerEvent,
} from "@react-native-community/datetimepicker";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

interface EndTimePickerSheetProps {
  visible: boolean;
  startedAt: string;
  elapsedLabel: string;
  onConfirm: (endedAt: Date) => void;
  onCancel: () => void;
}

export function EndTimePickerSheet({
  visible,
  startedAt,
  elapsedLabel,
  onConfirm,
  onCancel,
}: EndTimePickerSheetProps) {
  const insets = useSafeAreaInsets();
  const startDate = new Date(startedAt);
  const [selectedTime, setSelectedTime] = useState(
    () => new Date(startDate.getTime() + 60 * 60 * 1000),
  );

  // Reset to default when sheet opens with a new startedAt
  const [lastStartedAt, setLastStartedAt] = useState(startedAt);
  if (startedAt !== lastStartedAt) {
    setLastStartedAt(startedAt);
    setSelectedTime(new Date(new Date(startedAt).getTime() + 60 * 60 * 1000));
  }

  const handleChange = (_event: DateTimePickerEvent, date?: Date) => {
    if (date) setSelectedTime(date);
  };

  // Validation: must be after start and not in the future
  const now = new Date();
  const isBeforeStart = selectedTime <= startDate;
  const isInFuture = selectedTime > now;
  const isInvalid = isBeforeStart || isInFuture;

  const errorMessage = isBeforeStart
    ? "Must be after session start"
    : isInFuture
      ? "Cannot be in the future"
      : null;

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onCancel}
    >
      {/* Backdrop */}
      <Pressable
        className="flex-1"
        onPress={onCancel}
        style={{ backgroundColor: "rgba(0, 0, 0, 0.6)" }}
      />

      {/* Sheet */}
      <View
        className="rounded-t-3xl px-5 pt-6"
        style={{
          backgroundColor: colors.bg.surface1,
          paddingBottom: Math.max(insets.bottom, 20),
        }}
      >
        <ThemedText variant="title-2">
          Session ran for {elapsedLabel}
        </ThemedText>
        <ThemedText
          variant="body"
          color={colors.text.secondary}
          style={{ marginTop: 4 }}
        >
          Started at {startDate.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}. When did it actually end?
        </ThemedText>

        {/* Native time picker */}
        <View className="items-center my-4">
          <DateTimePicker
            value={selectedTime}
            mode="time"
            display={Platform.OS === "ios" ? "spinner" : "default"}
            onChange={handleChange}
            minimumDate={startDate}
            maximumDate={now}
            themeVariant="dark"
          />
        </View>

        {/* Validation error */}
        {errorMessage && (
          <ThemedText
            variant="body-small"
            color={colors.red[500]}
            style={{ textAlign: "center", marginBottom: 8 }}
          >
            {errorMessage}
          </ThemedText>
        )}

        {/* Cancel / Confirm buttons */}
        <View className="flex-row gap-3 mt-2">
          <Pressable
            onPress={onCancel}
            className="flex-1 py-3.5 rounded-xl items-center"
            style={{ backgroundColor: colors.bg.surface2 }}
          >
            <ThemedText variant="body-medium" color={colors.text.secondary}>
              Cancel
            </ThemedText>
          </Pressable>
          <Pressable
            onPress={() => onConfirm(selectedTime)}
            disabled={isInvalid}
            className="flex-1 py-3.5 rounded-xl items-center"
            style={{
              backgroundColor: isInvalid
                ? colors.bg.surface2
                : colors.blue[500],
              opacity: isInvalid ? 0.5 : 1,
            }}
          >
            <ThemedText
              variant="body-medium"
              color={isInvalid ? colors.text.tertiary : colors.text.inverse}
            >
              Confirm
            </ThemedText>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}
