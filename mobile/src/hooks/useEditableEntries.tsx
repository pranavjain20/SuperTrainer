/**
 * Shared edit state + mutation wiring for entry cards.
 *
 * Used by both Timeline (recording screen) and ExpandableSessionCard
 * (client profile) to avoid duplicating modal handling logic.
 */

import { useState } from "react";
import { Alert } from "react-native";

import type { SessionEntry, SessionEntryUpdate } from "@/src/api/types";
import { ExerciseEditModal } from "@/src/components/ExerciseEditModal";
import { ObservationEditModal } from "@/src/components/ObservationEditModal";
import { useEntryMutations } from "@/src/hooks/useEntryMutations";

export function useEditableEntries(sessionId: string) {
  const [editingEntry, setEditingEntry] = useState<SessionEntry | null>(null);
  const { updateMutation, deleteMutation } = useEntryMutations(sessionId);
  const isMutating = updateMutation.isPending || deleteMutation.isPending;

  const handleSave = (data: SessionEntryUpdate) => {
    if (!editingEntry) return;
    updateMutation.mutate(
      { entryId: editingEntry.id, data },
      {
        onSuccess: () => setEditingEntry(null),
        onError: (err) => Alert.alert("Save Failed", err.message),
      },
    );
  };

  const handleDelete = () => {
    if (!editingEntry) return;
    deleteMutation.mutate(editingEntry.id, {
      onSuccess: () => setEditingEntry(null),
      onError: (err) => Alert.alert("Delete Failed", err.message),
    });
  };

  const editModals = (
    <>
      {editingEntry?.entry_type === "exercise_card" && (
        <ExerciseEditModal
          entry={editingEntry}
          visible
          isSaving={isMutating}
          onSave={handleSave}
          onDelete={handleDelete}
          onClose={() => !isMutating && setEditingEntry(null)}
        />
      )}
      {editingEntry?.entry_type === "observation_card" && (
        <ObservationEditModal
          entry={editingEntry}
          visible
          isSaving={isMutating}
          onSave={handleSave}
          onDelete={handleDelete}
          onClose={() => !isMutating && setEditingEntry(null)}
        />
      )}
    </>
  );

  return { editingEntry, setEditingEntry, editModals };
}
