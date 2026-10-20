import { useEffect, useRef, useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Check, Landmark, Receipt, Target, X } from "lucide-react";

import { Button, Input, Select, Switch } from "@/shared/components";
import { numberFormat } from "@/i18n/format";
import type { ChatMessage } from "@/stores/AssistantStore";
import { useStores } from "@/stores/StoreContext";

const WHOLE = numberFormat({ maximumFractionDigits: 2 });
const DAYS = Array.from({ length: 28 }, (_, i) => i + 1);
const ICONS = { budget: Target, income: Landmark, bill: Receipt } as const;

type Fields = Record<string, unknown>;

const text = (value: unknown): string =>
  typeof value === "string" || typeof value === "number" ? String(value) : "";

/**
 * A proposed action, shown as the screen it belongs to shows it (F21.7.1, ADR-0025): every
 * field can be changed, and Approve — a tap, or saying "approve" — writes it; Cancel turns
 * it down. Once saved or cancelled it only says so, with a way to the screen it changed.
 */
export const ApproveCard = observer(function ApproveCard({
  message,
  today,
}: {
  message: ChatMessage;
  today: string;
}) {
  const { assistantStore, authStore, householdStore } = useStores();
  const { t } = useTranslation("assistant");
  const currency = authStore.user?.currency ?? "PLN";
  const card = message.card;
  const [fields, setFields] = useState<Fields>(card?.fields ?? {});
  const [busy, setBusy] = useState(false);
  const approve = () => {
    setBusy(true);
    void assistantStore.save(message, fields, today).finally(() => {
      setBusy(false);
    });
  };
  // Saying "approve" saves the latest waiting card with the fields as the user left them.
  const heard = useRef(assistantStore.approveSignal);
  useEffect(() => {
    if (assistantStore.approveSignal === heard.current) return;
    heard.current = assistantStore.approveSignal;
    if (assistantStore.waitingCard?.id === message.id) approve();
  });
  if (!card) return null;
  const Icon = ICONS[card.kind];
  const proposed = message.card_state === "proposed";
  const set = (name: string) => (value: unknown) => {
    setFields((f) => ({ ...f, [name]: value }));
  };
  const amount = (
    <Input
      label={t("card.amount", { currency })}
      inputMode="decimal"
      value={text(fields.amount)}
      disabled={!proposed}
      onChange={(e) => {
        set("amount")(e.target.value.replace(",", ".").replace(/\s/g, ""));
      }}
    />
  );

  return (
    <article
      aria-label={t(`card.${card.kind}`)}
      className="on-surface flex flex-col gap-3 rounded-card border-2 border-primary bg-surface p-4"
    >
      <span className="flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded-control bg-tone-primary-bg text-primary">
          <Icon size={18} aria-hidden="true" />
        </span>
        <span className="text-lg font-extrabold">{t(`card.${card.kind}`)}</span>
        {!proposed && (
          <span className="ml-auto rounded-pill bg-muted px-2 py-0.5 text-xs font-extrabold">
            {message.card_state === "saved" ? t("card.saved") : t("card.dismissed")}
          </span>
        )}
      </span>

      {card.kind === "budget" && amount}
      {card.kind === "income" && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {amount}
          <Input
            type="date"
            label={t("card.received_on")}
            value={text(fields.received_on)}
            disabled={!proposed}
            onChange={(e) => {
              set("received_on")(e.target.value);
            }}
          />
          <Input
            label={t("card.source")}
            value={text(fields.source)}
            maxLength={80}
            disabled={!proposed}
            containerClassName="md:col-span-2"
            onChange={(e) => {
              set("source")(e.target.value);
            }}
          />
        </div>
      )}
      {card.kind === "bill" && (
        <div className="grid grid-cols-2 gap-3">
          <Input
            label={t("card.name")}
            value={text(fields.name)}
            maxLength={80}
            disabled={!proposed}
            containerClassName="col-span-2"
            onChange={(e) => {
              set("name")(e.target.value);
            }}
          />
          {amount}
          <Select
            label={t("card.day")}
            value={text(fields.day)}
            disabled={!proposed}
            onChange={(e) => {
              set("day")(e.target.value === "" ? null : Number(e.target.value));
            }}
          >
            <option value="">{t("card.anyDay")}</option>
            {DAYS.map((day) => (
              <option key={day} value={day}>
                {day}
              </option>
            ))}
            <option value="31">{t("card.lastDay")}</option>
          </Select>
        </div>
      )}
      {card.kind !== "budget" && householdStore.mayShare && (
        <Switch
          checked={fields.shared === true}
          disabled={!proposed}
          onChange={set("shared")}
          label={t("card.shared")}
        />
      )}

      {proposed ? (
        <div className="flex flex-col gap-1.5">
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="secondary"
              className="min-h-11"
              disabled={busy}
              onClick={() => void assistantStore.dismiss(message)}
            >
              <X size={16} aria-hidden="true" />
              {t("card.dismiss")}
            </Button>
            <Button className="min-h-11" disabled={busy} onClick={approve}>
              <Check size={16} aria-hidden="true" />
              {t("card.approve")}
            </Button>
          </div>
          <span className="text-center text-sm text-muted-foreground">{t("card.sayApprove")}</span>
        </div>
      ) : (
        message.card_state === "saved" && (
          <span className="flex items-center justify-between gap-3 text-md">
            <span className="font-bold tabular-nums">
              {WHOLE.format(Number(fields.amount))} {currency}
            </span>
            <Link to="/plan" className="font-bold text-primary">
              {t("card.openPlan")}
            </Link>
          </span>
        )
      )}
    </article>
  );
});
