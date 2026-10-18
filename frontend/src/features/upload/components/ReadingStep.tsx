import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Container } from "@/shared/components/Layout/Layout";
import { useStores } from "@/stores/StoreContext";

/** Widths of the printed lines drawn on the paper, as a share of its width. */
const PAPER_LINES = ["70%", "45%", "85%", "60%", "80%", "50%", "75%", "40%", "65%", "30%"];

/**
 * What the user sees while the photos are read (upload-reading.html): a receipt with a
 * light passing down it, and how many of the receipts are done when there are several.
 * Reading runs on the server, so this only waits; the result replaces it.
 */
export const ReadingStep = observer(function ReadingStep() {
  const { uploadStore } = useStores();
  const { t } = useTranslation("upload");
  const many = uploadStore.lines.length > 1;

  return (
    <Container size="narrow" gutter={false} className="py-10 md:py-16">
      <section
        aria-live="polite"
        aria-busy="true"
        className="mx-auto flex max-w-sm flex-col items-center gap-6 text-center"
      >
        <div
          aria-hidden="true"
          className="relative flex h-62 w-42 flex-col gap-2.25 overflow-hidden rounded-control bg-surface px-4.5 py-5.5 shadow-lg"
        >
          {PAPER_LINES.map((width, i) => (
            <span key={i} className="h-1.5 rounded-pill bg-border-strong" style={{ width }} />
          ))}
          <span className="absolute inset-x-0 h-0.75 animate-scan bg-primary shadow-[0_0_18px_var(--color-primary)] motion-reduce:animate-none" />
        </div>
        <div className="flex flex-col gap-1.5">
          <h1 className="m-0 text-2xl font-extrabold">
            {many ? t("reading.titleMany") : t("reading.title")}
          </h1>
          <p className="m-0 text-base text-muted-foreground">{t("reading.hint")}</p>
        </div>
        {many && uploadStore.totalItems > 0 && (
          <p className="m-0 text-md font-semibold text-muted-foreground tabular-nums">
            {t("reading.progress", {
              done: uploadStore.processedItems,
              total: uploadStore.totalItems,
            })}
          </p>
        )}
      </section>
    </Container>
  );
});
