import { Text, type TextProps, type TextStyle } from "react-native";

import { colors, typography, type TypographyVariant } from "@/src/constants/tokens";

interface ThemedTextProps extends TextProps {
  /** Typography variant from the design system scale. Defaults to "body". */
  variant?: TypographyVariant;
  /** Override text color. Defaults to text.primary. */
  color?: string;
}

/**
 * Themed Text wrapper — applies design system typography.
 *
 * Usage:
 *   <ThemedText variant="title-2">Goblet Squat</ThemedText>
 *   <ThemedText variant="data">120</ThemedText>
 *   <ThemedText variant="caption" color={colors.text.secondary}>SET</ThemedText>
 */
export function ThemedText({
  variant = "body",
  color = colors.text.primary,
  style,
  ...rest
}: ThemedTextProps) {
  const variantStyle = typography[variant] as TextStyle;

  return <Text style={[variantStyle, { color }, style]} {...rest} />;
}
