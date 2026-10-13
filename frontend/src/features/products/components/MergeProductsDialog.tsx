import { useId, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Button, Modal, ModalBody, ModalFooter, ModalHeader } from "@/shared/components";
import { useStores } from "@/stores/StoreContext";

/**
 * Folding the ticked products into one (F16.1): the user picks which name stays, and
 * the others' purchases and ways of printing join it.
 */
export const MergeProductsDialog = observer(function MergeProductsDialog({
  onClose,
}: {
  onClose: () => void;
}) {
  const { productsStore } = useStores();
  const { t } = useTranslation(["products", "common"]);
  const titleId = useId();
  const chosen = productsStore.selectedProducts;
  const [target, setTarget] = useState(chosen[0]?.id ?? "");

  const merge = async () => {
    if (await productsStore.merge(target)) onClose();
  };

  return (
    <Modal isOpen onClose={onClose} aria-labelledby={titleId} className="md:w-[480px]">
      <ModalHeader>
        <h2 id={titleId} className="m-0 text-[17px] font-bold">
          {t("merge.title", { count: chosen.length })}
        </h2>
      </ModalHeader>
      <ModalBody className="flex flex-col gap-3">
        <p className="m-0 text-md text-muted-foreground">{t("merge.hint")}</p>
        <fieldset className="m-0 flex flex-col gap-1 border-0 p-0">
          <legend className="mb-1.5 p-0 text-base font-medium text-muted-foreground">
            {t("merge.keep")}
          </legend>
          {chosen.map((product) => (
            <label
              key={product.id}
              className="flex min-h-11 cursor-pointer items-center gap-3 rounded-control px-2 hover:bg-muted"
            >
              <input
                type="radio"
                name="merge-target"
                className="h-4 w-4 accent-primary"
                checked={target === product.id}
                onChange={() => {
                  setTarget(product.id);
                }}
              />
              <span className="min-w-0 break-words text-md">{product.name}</span>
            </label>
          ))}
        </fieldset>
      </ModalBody>
      <ModalFooter>
        <span className="hidden md:block" />
        <div className="flex w-full items-center gap-2.5 md:w-auto [&>*]:flex-1 md:[&>*]:flex-none">
          <Button type="button" variant="ghost" onClick={onClose}>
            {t("common:cancel")}
          </Button>
          <Button
            type="button"
            variant="primary"
            disabled={!target || productsStore.isSaving}
            onClick={() => void merge()}
          >
            {t("merge.confirm")}
          </Button>
        </div>
      </ModalFooter>
    </Modal>
  );
});
