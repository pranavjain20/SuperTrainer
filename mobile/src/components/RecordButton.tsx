/**
 * Floating record button (FAB) with pulsing ring effect.
 *
 * Visual states:
 * - Idle: 64px blue circle with mic icon, bottom-right corner
 * - Recording: red circle with stop icon + pulsing ring + duration badge
 * - Disabled: 50% opacity, no press handler
 *
 * Positioned absolutely — takes zero layout space. The parent must
 * pass `bottom` to account for safe area insets.
 */

import FontAwesome from "@expo/vector-icons/FontAwesome";
import * as Haptics from "expo-haptics";
import { useCallback, useEffect, useRef } from "react";
import { Animated, Easing, Pressable, Text, View } from "react-native";

import { ThemedText } from "@/src/components/ThemedText";
import { colors } from "@/src/constants/tokens";

interface RecordButtonProps {
  isRecording: boolean;
  duration: number;
  onPress: () => void;
  disabled?: boolean;
  bottom: number;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

const BUTTON_SIZE = 72;
const RECORDING_SIZE = 88;
const RECORDING_SCALE = RECORDING_SIZE / BUTTON_SIZE; // ~1.22

export function RecordButton({
  isRecording,
  duration,
  onPress,
  disabled,
  bottom,
}: RecordButtonProps) {
  const pulseScale = useRef(new Animated.Value(1)).current;
  const pulseOpacity = useRef(new Animated.Value(0)).current;
  const buttonScale = useRef(new Animated.Value(1)).current;
  const animationRef = useRef<Animated.CompositeAnimation | null>(null);

  useEffect(() => {
    if (isRecording) {
      Animated.timing(buttonScale, {
        toValue: RECORDING_SCALE,
        duration: 250,
        easing: Easing.out(Easing.back(1.4)),
        useNativeDriver: true,
      }).start();

      pulseScale.setValue(1);
      pulseOpacity.setValue(0.4);

      const animation = Animated.loop(
        Animated.sequence([
          Animated.parallel([
            Animated.timing(pulseScale, {
              toValue: 1.8,
              duration: 1400,
              useNativeDriver: true,
            }),
            Animated.timing(pulseOpacity, {
              toValue: 0,
              duration: 1400,
              useNativeDriver: true,
            }),
          ]),
          Animated.parallel([
            Animated.timing(pulseScale, {
              toValue: 1,
              duration: 0,
              useNativeDriver: true,
            }),
            Animated.timing(pulseOpacity, {
              toValue: 0.4,
              duration: 0,
              useNativeDriver: true,
            }),
          ]),
        ]),
      );

      animationRef.current = animation;
      animation.start();
    } else {
      Animated.timing(buttonScale, {
        toValue: 1,
        duration: 200,
        easing: Easing.out(Easing.ease),
        useNativeDriver: true,
      }).start();

      if (animationRef.current) {
        animationRef.current.stop();
        animationRef.current = null;
      }

      Animated.parallel([
        Animated.timing(pulseScale, {
          toValue: 1,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.timing(pulseOpacity, {
          toValue: 0,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start();
    }

    return () => {
      if (animationRef.current) {
        animationRef.current.stop();
        animationRef.current = null;
      }
    };
  }, [isRecording, pulseScale, pulseOpacity, buttonScale]);

  const buttonColor = isRecording ? colors.recording.red : colors.blue[500];

  const lastPressRef = useRef(0);

  const handlePress = useCallback(() => {
    if (disabled) return;
    const now = Date.now();
    if (now - lastPressRef.current < 400) return;
    lastPressRef.current = now;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    onPress();
  }, [disabled, onPress]);

  return (
    <View
      style={{
        position: "absolute",
        right: 20,
        bottom: bottom + 16,
        alignItems: "center",
        zIndex: 10,
      }}
    >
      {/* Duration badge — floats above button when recording */}
      {isRecording && (
        <View
          className="rounded-full px-3 py-1 mb-2"
          style={{ backgroundColor: colors.recording.red }}
        >
          <ThemedText variant="data" color={colors.text.primary} style={{ fontSize: 12 }}>
            {formatDuration(duration)}
          </ThemedText>
        </View>
      )}

      {/* Button + pulse ring */}
      <View
        className="items-center justify-center"
        style={{ width: BUTTON_SIZE, height: BUTTON_SIZE, overflow: "visible" }}
      >
        {/* Pulse ring */}
        <Animated.View
          style={{
            position: "absolute",
            width: BUTTON_SIZE,
            height: BUTTON_SIZE,
            borderRadius: BUTTON_SIZE / 2,
            backgroundColor: buttonColor,
            transform: [{ scale: pulseScale }],
            opacity: pulseOpacity,
          }}
        />

        {/* Shadow + main button — mic button is the ONLY shadow in the app */}
        <Animated.View
          style={{
            transform: [{ scale: buttonScale }],
            shadowColor: buttonColor,
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.25,
            shadowRadius: 16,
            elevation: 6,
          }}
        >
          <Pressable
            onPress={handlePress}
            disabled={disabled}
            style={{
              width: BUTTON_SIZE,
              height: BUTTON_SIZE,
              borderRadius: BUTTON_SIZE / 2,
              backgroundColor: buttonColor,
              alignItems: "center",
              justifyContent: "center",
              opacity: disabled ? 0.5 : 1,
            }}
          >
            <FontAwesome
              name={isRecording ? "stop" : "microphone"}
              size={isRecording ? 24 : 28}
              color={colors.text.primary}
            />
          </Pressable>
        </Animated.View>
      </View>
    </View>
  );
}
