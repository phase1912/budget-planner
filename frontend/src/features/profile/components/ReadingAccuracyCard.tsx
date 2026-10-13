import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";

import { Meter } from "@/shared/components";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { dateFormat, numberFormat } from "@/i18n/format";
import { useStores } from "@/stores/StoreContext";

const MONTH = dateFormat({ month: "short", year: "numeric" });
const SHARE = numberFormat({ style: "percent", maximumFractionDigits: 0 });

/**
 * How often reading a receipt needed the user's correction (F15.4): the share of
 * receipts corrected over the last six months, the shops behind most corrections, and
 * the month-by-month trend — measured from what the user actually changed.
 */
export const ReadingAccuracyCard = observer(function ReadingAccuracyCard() {
  const { accuracyStore } = useStores();
  const { t } = useTranslation("profile");
  const report = accuracyStore.report;

  useEffect(() => {
    void accuracyStore.load();
  }, [accuracyStore]);

  if (!report) return null;
  const share = (corrected: number, receipts: number) =>
    receipts > 0 ? SHARE.format(corrected / receipts) : "—";

  return (
    <Card variant="surface" flush>
      <CardHeader>{t("accuracy.title")}</CardHeader>
      <CardBody className="flex flex-col gap-5">
        {report.receipts === 0 ? (
          <p className="m-0 text-md text-muted-foreground">{t("accuracy.empty")}</p>
        ) : (
          <>
            <div className="flex flex-col gap-1">
              <p className="m-0 text-lg font-semibold">
                {t("accuracy.headline", {
                  count: report.receipts,
                  corrected: report.corrected_receipts,
                  share: share(report.corrected_receipts, report.receipts),
                })}
              </p>
              <p className="m-0 text-md leading-relaxed text-muted-foreground">
                {t("accuracy.lines", {
                  count: report.lines,
                  corrected: report.corrected_lines,
                })}{" "}
                {report.remembered_lines > 0 &&
                  t("accuracy.remembered", { count: report.remembered_lines })}
              </p>
            </div>

            {report.shops.length > 0 && (
              <section className="flex flex-col gap-2">
                <h3 className="m-0 text-md font-semibold">{t("accuracy.shops")}</h3>
                <ul className="m-0 flex list-none flex-col divide-y divide-border rounded-control border border-border p-0">
                  {report.shops.map((shop) => (
                    <li
                      key={shop.merchant}
                      className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 px-3 py-2.5"
                    >
                      <span className="min-w-0 break-words text-md font-medium">
                        {shop.merchant}
                      </span>
                      <span className="text-base tabular-nums text-muted-foreground">
                        {t("accuracy.ofReceipts", {
                          count: shop.receipts,
                          corrected: shop.corrected,
                        })}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <section className="flex flex-col gap-2">
              <h3 className="m-0 text-md font-semibold">{t("accuracy.trend")}</h3>
              <ul
                aria-label={t("accuracy.trend")}
                className="m-0 flex list-none flex-col gap-2.5 p-0"
              >
                {report.months.map((month) => (
                  <li
                    key={month.month}
                    className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 md:grid-cols-[7rem_minmax(0,1fr)_8rem]"
                  >
                    <span className="text-base text-muted-foreground">
                      {MONTH.format(new Date(`${month.month}T00:00:00`))}
                    </span>
                    <span className="order-3 col-span-2 md:order-none md:col-span-1">
                      <Meter
                        value={month.receipts > 0 ? (month.corrected / month.receipts) * 100 : 0}
                      />
                    </span>
                    <span className="text-right text-base tabular-nums text-muted-foreground">
                      {month.receipts > 0
                        ? t("accuracy.ofReceipts", {
                            count: month.receipts,
                            corrected: month.corrected,
                          })
                        : t("accuracy.noReceipts")}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </CardBody>
    </Card>
  );
});
