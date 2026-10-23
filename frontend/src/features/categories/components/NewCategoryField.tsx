import { useEffect, useRef, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/** The option value a category list ends with, asking for a new category (F5.9). */
export const NEW_CATEGORY = "__new_category__";

/** The "＋ New category" option a category list ends with (F5.9). */
export function NewCategoryOption() {
  const { t } = useTranslation("categories");
  return <option value={NEW_CATEGORY}>{t("inline.option")}</option>;
}

/**
 * A new category's name, asked where a category is being chosen (BRD C6 — F5.9): made as
 * on the Categories screen, with its errors, and handed back by id to be selected. Enter
 * creates it rather than submitting the form around it.
 */
export const NewCategoryField = observer(function NewCategoryField({
  onCreated,
  onCancel,
}: {
  onCreated: (id: string) => void;
  onCancel: () => void;
}) {
  const { categoriesStore } = useStores();
  const { t } = useTranslation("categories");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [saving, setSaving] = useState(false);
  const field = useRef<HTMLInputElement>(null);

  // The user just asked to name one: the name is where typing goes next.
  useEffect(() => {
    field.current?.focus();
  }, []);

  const create = async () => {
    if (name.trim() === "" || saving) return;
    setSaving(true);
    const made = await categoriesStore.addCategory(name.trim());
    setSaving(false);
    if ("error" in made) {
      setError(made.error);
      return;
    }
    onCreated(made.id);
  };

  return (
    <div className="flex flex-col gap-2 rounded-control border border-border p-3">
      <Input
        label={t("inline.name")}
        value={name}
        maxLength={100}
        placeholder={t("inline.placeholder")}
        error={error}
        ref={field}
        onChange={(e) => {
          setName(e.target.value);
          setError(undefined);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            void create();
          }
        }}
      />
      <div className="flex gap-2 [&>*]:flex-1 md:justify-end md:[&>*]:flex-none">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          {t("create.cancel")}
        </Button>
        <Button
          type="button"
          size="sm"
          disabled={name.trim() === "" || saving}
          onClick={() => void create()}
        >
          {t("inline.create")}
        </Button>
      </div>
    </div>
  );
});
