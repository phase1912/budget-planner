import { useEffect, useId, useRef, useState } from "react";
import { observer } from "mobx-react-lite";
import { Plus } from "lucide-react";

import { Button, IconTile, Input, Modal } from "@/shared/components";

interface CreateCategoryDialogProps {
  /** Resolves to null on success, or to the reason the server refused the name. */
  onCreate: (name: string) => Promise<string | null>;
  onClose: () => void;
}

/**
 * Names a new custom category (BRD C6).
 *
 * A dialog rather than a row appended below the list: the "New category"
 * button sits at the top of a long page, and the form must appear where the
 * user is looking. A refused name is explained next to the field, so it can
 * be corrected without losing what was typed.
 */
export const CreateCategoryDialog = observer(function CreateCategoryDialog({
  onCreate,
  onClose,
}: CreateCategoryDialogProps) {
  const titleId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    // The user opened this dialog to type a name; the field is where they start.
    input.current?.focus();
  }, []);

  const submit = async () => {
    if (!name.trim() || isSaving) return;
    setIsSaving(true);
    const refused = await onCreate(name.trim());
    setIsSaving(false);
    if (refused) setError(refused);
    else onClose();
  };

  return (
    <Modal isOpen onClose={onClose} aria-labelledby={titleId} className="w-full max-w-[460px]">
      <form
        className="flex flex-col gap-4.5 p-6"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <div className="flex items-start gap-3.5">
          <IconTile tone="success" size="lg">
            <Plus size={20} />
          </IconTile>
          <div className="flex flex-col gap-1.25">
            <h2 id={titleId} className="m-0 text-[17px] font-bold text-foreground">
              New category
            </h2>
            <p className="m-0 text-lg text-muted-foreground">
              You and the agent can file items under it as soon as it is created.
            </p>
          </div>
        </div>

        <Input
          ref={input}
          id={`${titleId}-name`}
          label="Name"
          placeholder="e.g. Pet Supplies"
          maxLength={100}
          value={name}
          error={error}
          onChange={(e) => {
            setName(e.target.value);
            setError(undefined);
          }}
        />

        <div className="flex flex-wrap items-center justify-end gap-2.5">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!name.trim() || isSaving}>
            Create category
          </Button>
        </div>
      </form>
    </Modal>
  );
});
