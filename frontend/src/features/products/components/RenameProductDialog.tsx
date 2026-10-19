import { useId, useRef, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Input, Modal, ModalBody, ModalFooter, ModalHeader } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/**
 * Giving a product the name it is shown under (F16.1) — for one read wrongly or printed
 * cryptically. How receipts print it is kept, so later receipts still find it.
 */
export const RenameProductDialog = observer(function RenameProductDialog({
  productId,
  current,
  onClose,
  onRenamed,
}: {
  productId: string;
  current: string;
  onClose: () => void;
  onRenamed?: () => void;
}) {
  const { productsStore } = useStores();
  const { t } = useTranslation(["products", "common"]);
  const titleId = useId();
  const field = useRef<HTMLInputElement>(null);
  const [name, setName] = useState(current);
  const unchanged = name.trim() === current || !name.trim();

  return (
    <Modal
      isOpen
      onClose={onClose}
      aria-labelledby={titleId}
      initialFocus={field}
      className="md:w-[440px]"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (unchanged) return;
          void productsStore.rename(productId, name).then((ok) => {
            if (!ok) return;
            onRenamed?.();
            onClose();
          });
        }}
      >
        <ModalHeader>
          <h2 id={titleId} className="m-0 text-[17px] font-bold">
            {t("rename.title")}
          </h2>
        </ModalHeader>
        <ModalBody className="flex flex-col gap-3">
          <Input
            ref={field}
            label={t("rename.name")}
            value={name}
            maxLength={255}
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
          <p className="m-0 text-md text-muted-foreground">{t("rename.hint")}</p>
        </ModalBody>
        <ModalFooter>
          <span className="hidden md:block" />
          <div className="flex w-full items-center gap-2.5 md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
            <Button type="button" variant="ghost" onClick={onClose}>
              {t("common:cancel")}
            </Button>
            <Button type="submit" variant="primary" disabled={unchanged || productsStore.isSaving}>
              {t("rename.save")}
            </Button>
          </div>
        </ModalFooter>
      </form>
    </Modal>
  );
});
