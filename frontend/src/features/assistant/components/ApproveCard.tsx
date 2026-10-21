import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Landmark, Receipt, ShoppingBag, Target, type LucideIcon } from "lucide-react";

import { Input, RepeatField, Select, Switch } from "@/shared/components";
import { useCardName } from "@/features/money-accounts/components/newCard";
import { numberFormat } from "@/i18n/format";
import { categoryName } from "@/shared/categoryName";
import type { ChatMessage } from "@/stores/AssistantStore";
import { useStores } from "@/stores/StoreContext";
import { CardShell } from "./CardShell";
import { isOwn, type OwnKind } from "./cardKinds";
import { useApproval } from "./useApproval";

const WHOLE = numberFormat({ maximumFractionDigits: 2 });
const ICONS: Record<OwnKind, LucideIcon> = {
  budget: Target,
  income: Landmark,
  bill: Receipt,
  expense: ShoppingBag,
};

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
  const { authStore, householdStore, categoriesStore, bankAccountsStore } = useStores();
  const cardName = useCardName();
  const { t } = useTranslation("assistant");
  const currency = authStore.user?.currency ?? "PLN";
  const card = message.card;
  const [fields, setFields] = useState<Fields>(card?.fields ?? {});
  const { busy, approve } = useApproval(message, fields, today);
  // Other kinds are an answer (`AnswerCard`) or drawn from their form (`FormCard`).
  if (!card || !isOwn(card.kind)) return null;
  const kind = card.kind;
  const Icon = ICONS[kind];
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
    <CardShell
      message={message}
      title={t(`card.${kind}`)}
      icon={Icon}
      busy={busy}
      onApprove={approve}
      done={
        <span className="flex items-center justify-between gap-3 text-md">
          <span className="font-bold tabular-nums">
            {WHOLE.format(Number(fields.amount))} {currency}
          </span>
          {kind === "expense" ? (
            <Link to="/receipts" className="font-bold text-primary">
              {t("card.openReceipts")}
            </Link>
          ) : (
            <Link to="/plan" className="font-bold text-primary">
              {t("card.openPlan")}
            </Link>
          )}
        </span>
      }
    >
      {kind === "budget" && amount}
      {kind === "expense" && (
        <div className="grid grid-cols-2 gap-3">
          <Input
            label={t("card.description")}
            value={text(fields.description)}
            maxLength={255}
            disabled={!proposed}
            containerClassName="col-span-2"
            onChange={(e) => {
              set("description")(e.target.value);
            }}
          />
          {amount}
          <Input
            type="date"
            label={t("card.spent_on")}
            value={text(fields.spent_on)}
            disabled={!proposed}
            onChange={(e) => {
              set("spent_on")(e.target.value);
            }}
          />
          <div className="col-span-2">
            <Select
              label={t("card.category")}
              value={text(fields.category_id)}
              disabled={!proposed}
              onChange={(e) => {
                set("category_id")(e.target.value);
              }}
            >
              {categoriesStore.categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {categoryName(c.name)}
                </option>
              ))}
            </Select>
          </div>
        </div>
      )}
      {kind === "income" && (
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
          {/* Income lands on a card (F23.21): with none yet, approving makes one. */}
          {proposed && bankAccountsStore.loaded && bankAccountsStore.accounts.length === 0 && (
            <p className="m-0 text-md text-muted-foreground md:col-span-2">
              {t("card.newCard", { name: cardName(fields.shared === true) })}
            </p>
          )}
        </div>
      )}
      {kind === "bill" && (
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
          <div className="col-span-2">
            <RepeatField
              value={{
                day: typeof fields.day === "number" ? fields.day : null,
                weekday: typeof fields.weekday === "number" ? fields.weekday : null,
              }}
              onChange={(repeat) => {
                setFields((f) => ({ ...f, day: repeat.day, weekday: repeat.weekday }));
              }}
            />
          </div>
        </div>
      )}
      {(kind === "income" || kind === "bill") && householdStore.mayShare && (
        <Switch
          checked={fields.shared === true}
          disabled={!proposed}
          onChange={set("shared")}
          label={t("card.shared")}
        />
      )}
    </CardShell>
  );
});
