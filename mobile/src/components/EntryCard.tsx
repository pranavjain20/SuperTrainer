import type { SessionEntry } from "@/src/api/types";
import { ExerciseCard } from "./ExerciseCard";
import { ObservationCard } from "./ObservationCard";

interface EntryCardProps {
  entry: SessionEntry;
  exerciseNumber?: number;
  onPress?: () => void;
  /** When true, renders without its own card wrapper (for use inside a parent container). */
  contained?: boolean;
}

export function EntryCard({ entry, exerciseNumber, onPress, contained }: EntryCardProps) {
  if (entry.entry_type === "observation_card") {
    return <ObservationCard entry={entry} onPress={onPress} contained={contained} />;
  }
  return <ExerciseCard entry={entry} exerciseNumber={exerciseNumber} onPress={onPress} contained={contained} />;
}
