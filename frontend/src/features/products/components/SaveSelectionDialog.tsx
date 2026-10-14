import { useId, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, ModalFooter, ModalHeader } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/** Saving the ticked products under a name, to open them together again (F16.2). */
export const SaveSelectionDialog = observer(function SaveSelectionDialog({
  onClose,
}: {
  onClose: () => void;
}) {
  const { explorationStore } = useStores();
  const { t } = useTranslation(["products", "common"]);
  const titleId = useId();
  const [name, setName] = useState("");

  const save = async () => {
    if (name.trim() && (await explorationStore.saveSelection(name.trim()))) onClose();
  };

  return (
    <Modal isOpen onClose={onClose} aria-labelledby={titleId} className="md:w-[440px]">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <ModalHeader>
          <h2 id={titleId} className="m-0 text-[17px] font-bold">
            {t("selections.saveTitle")}
          </h2>
        </ModalHeader>
        <ModalBody className="flex flex-col gap-3">
          <Input
            label={t("selections.name")}
            value={name}
            maxLength={60}
            placeholder={t("selections.placeholder")}
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
        </ModalBody>
        <ModalFooter>
          <span className="hidden md:block" />
          <div className="flex w-full items-center gap-2.5 md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
            <Button type="button" variant="ghost" onClick={onClose}>
              {t("common:cancel")}
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={!name.trim() || explorationStore.isSaving}
            >
              {t("selections.save")}
            </Button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
});
