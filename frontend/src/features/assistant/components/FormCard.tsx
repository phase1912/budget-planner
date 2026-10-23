import { useState } from "react";
import { observer } from "mobx-react-lite";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  Flag,
  Landmark,
  Pencil,
  PlusCircle,
  ReceiptText,
  ShoppingBasket,
  Trash2,
  X,
  type LucideIcon,
} from "lucide-react";

import type { components } from "@/api/schema";
import { Input, RepeatField, Select, Switch } from "@/shared/components";
import { categoryName } from "@/shared/categoryName";
import type { ChatMessage } from "@/stores/AssistantStore";
import { useStores } from "@/stores/StoreContext";
import { CardShell } from "./CardShell";
import { useApproval } from "./useApproval";

type FormField = components["schemas"]["FormFieldRead"];
type Fields = Record<string, unknown>;

const DAYS = Array.from({ length: 30 }, (_, i) => i + 1);

const list = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
const text = (value: unknown): string =>
  typeof value === "string" || typeof value === "number" ? String(value) : "";
const number = (value: unknown): number | null => (typeof value === "number" ? value : null);
const decimal = (typed: string): string => typed.replace(",", ".").replace(/\s/g, "");

/** Kinds about money on a card: a balance set right, money in, out or moved (F21.10). */
const ON_A_CARD = ["account", "transfer", "balance", "money_", "move"];
const onACard = (kind: string) => ON_A_CARD.some((prefix) => kind.startsWith(prefix));

/** Kinds about one receipt: a line corrected, the receipt checked, deleted or told (F21.6). */
const ON_A_RECEIPT = ["line", "receipt_", "told_receipt", "category_move"];
const onAReceipt = (kind: string) => ON_A_RECEIPT.some((prefix) => kind.startsWith(prefix));

/** What a card changes: an icon that says add, change or remove — or the thing itself. */
function iconOf(kind: string): LucideIcon {
  if (/_(change)$/.test(kind) || kind === "line") return Pencil;
  if (/_(stop|remove|delete)$/.test(kind)) return Trash2;
  if (onAReceipt(kind)) return ReceiptText;
  if (kind.startsWith("goal")) return Flag;
  if (onACard(kind)) return Landmark;
  if (kind.startsWith("product")) return ShoppingBasket;
  return PlusCircle;
}

/** The screen a saved card's change can be seen on. */
function screenOf(kind: string): string {
  if (kind.startsWith("goal")) return "/goals";
  if (kind === "trip") return "/trips";
  if (kind.startsWith("admin")) return "/admin";
  if (kind === "setting" || kind.startsWith("family")) return "/settings";
  if (kind === "category") return "/categories";
  if (onAReceipt(kind)) return "/receipts";
  if (onACard(kind)) return "/accounts";
  if (kind.startsWith("product")) return "/products";
  return "/plan";
}

/**
 * A proposed action of any kind the app has no card of its own for (F21.7.1): drawn from
 * the form the server sends, field by field, every one editable but what it changes or
 * removes. Approve — a tap, or saying it — writes it; Cancel turns it down. A new kind of
 * action needs words for its title and fields, not a new card.
 */
export const FormCard = observer(function FormCard({
  message,
  today,
}: {
  message: ChatMessage;
  today: string;
}) {
  const { authStore, categoriesStore, bankAccountsStore, householdStore } = useStores();
  const { t } = useTranslation("assistant");
  // The card's words are named by the server's kinds and fields, not known in advance.
  const say = t as (key: string, options?: Record<string, unknown>) => string;
  const currency = authStore.user?.currency ?? "PLN";
  const card = message.card;
  const [fields, setFields] = useState<Fields>(card?.fields ?? {});
  const { busy, approve } = useApproval(message, fields, today);
  if (!card?.form) return null;
  const proposed = message.card_state === "proposed";
  const set = (name: string) => (value: unknown) => {
    setFields((f) => ({ ...f, [name]: value }));
  };
  const label = (name: string) => say(`card.fields.${name}`, { currency });

  const control = (field: FormField) => {
    const value = fields[field.name];
    // A difference only corrected records no purchase, so it needs no category or name.
    if (fields.way === "correct" && (field.name === "category_id" || field.name === "description"))
      return null;
    switch (field.kind) {
      case "target":
        return (
          <p
            key={field.name}
            className="m-0 rounded-control bg-muted px-3 py-2.5 text-lg font-bold"
          >
            {/* A setting is named by the server's key: the user reads its name (F21.11). */}
            {card.kind === "setting"
              ? text(value).replace(/^[a-z_]+:/, `${say(`card.settings.${text(fields.setting)}`)}:`)
              : text(value)}
          </p>
        );
      case "amount":
      case "balance":
      case "percent":
        return (
          <Input
            key={field.name}
            label={label(field.name)}
            inputMode="decimal"
            value={text(value)}
            disabled={!proposed}
            onChange={(e) => {
              set(field.name)(decimal(e.target.value));
            }}
          />
        );
      case "date":
        return (
          <Input
            key={field.name}
            type="date"
            label={label(field.name)}
            value={text(value)}
            disabled={!proposed}
            onChange={(e) => {
              set(field.name)(e.target.value);
            }}
          />
        );
      case "day":
        return (
          <Select
            key={field.name}
            label={label(field.name)}
            value={text(value)}
            disabled={!proposed}
            onChange={(e) => {
              set(field.name)(e.target.value === "" ? null : Number(e.target.value));
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
        );
      case "items": {
        // The names shown and the ids saved go side by side: "products" with "product_ids".
        const ids = field.name.replace(/s$/, "_ids");
        const names = list(value);
        return (
          <ul
            key={field.name}
            aria-label={label(field.name)}
            className="m-0 flex list-none flex-wrap gap-2 p-0"
          >
            {names.map((name, i) => (
              <li
                key={`${String(i)}-${name}`}
                className="flex min-h-11 max-w-full items-center gap-1 rounded-pill bg-muted pr-1 pl-3 text-md"
              >
                <span className="min-w-0 break-words">{name}</span>
                {proposed && names.length > 1 && (
                  <button
                    type="button"
                    aria-label={t("card.removeItem", { name })}
                    onClick={() => {
                      setFields((f) => ({
                        ...f,
                        [field.name]: names.filter((_, j) => j !== i),
                        [ids]: list(f[ids]).filter((_, j) => j !== i),
                      }));
                    }}
                    className="flex h-11 w-11 items-center justify-center rounded-pill"
                  >
                    <X size={16} aria-hidden="true" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        );
      }
      case "lines": {
        const lines = Array.isArray(value)
          ? value.filter((l): l is Fields => typeof l === "object" && l !== null)
          : [];
        const setLine = (i: number, change: Fields) => {
          set(field.name)(lines.map((l, j) => (j === i ? { ...l, ...change } : l)));
        };
        const sum = lines.reduce((s, l) => s + (Number(text(l.amount)) || 0), 0);
        return (
          <div key={field.name} className="flex flex-col gap-2">
            <span aria-hidden="true" className="text-base font-medium text-muted-foreground">
              {label(field.name)}
            </span>
            <ul aria-label={label(field.name)} className="m-0 flex list-none flex-col gap-2 p-0">
              {lines.map((line, i) => (
                <li key={i} className="flex items-end gap-2">
                  <Input
                    containerClassName="min-w-0 flex-1"
                    aria-label={t("card.lineName", { number: i + 1 })}
                    value={text(line.name)}
                    disabled={!proposed}
                    onChange={(e) => {
                      setLine(i, { name: e.target.value });
                    }}
                  />
                  <Input
                    containerClassName="w-24 shrink-0"
                    aria-label={t("card.lineAmount", { number: i + 1 })}
                    inputMode="decimal"
                    value={text(line.amount)}
                    disabled={!proposed}
                    onChange={(e) => {
                      setLine(i, { amount: decimal(e.target.value) });
                    }}
                  />
                  {proposed && lines.length > 1 && (
                    <button
                      type="button"
                      aria-label={t("card.removeItem", { name: text(line.name) })}
                      onClick={() => {
                        set(field.name)(lines.filter((_, j) => j !== i));
                      }}
                      className="flex h-12 w-11 shrink-0 items-center justify-center rounded-control"
                    >
                      <X size={16} aria-hidden="true" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <p className="m-0 text-right text-md font-bold tabular-nums">
              {t("card.linesTotal", { amount: sum.toFixed(2), currency })}
            </p>
          </div>
        );
      }
      case "repeat":
        return (
          <RepeatField
            key={field.name}
            value={{ day: number(fields.day), weekday: number(fields.weekday) }}
            onChange={(repeat) => {
              setFields((f) => ({ ...f, day: repeat.day, weekday: repeat.weekday }));
            }}
          />
        );
      case "category":
        return (
          <Select
            key={field.name}
            label={label(field.name)}
            value={text(value)}
            disabled={!proposed}
            onChange={(e) => {
              set(field.name)(e.target.value || null);
            }}
          >
            <option value="">—</option>
            {categoriesStore.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {categoryName(c.name)}
              </option>
            ))}
          </Select>
        );
      case "account":
        return (
          <Select
            key={field.name}
            label={label(field.name)}
            value={text(value)}
            disabled={!proposed}
            onChange={(e) => {
              set(field.name)(e.target.value);
            }}
          >
            {bankAccountsStore.accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        );
      case "choice":
        return (
          <Select
            key={field.name}
            label={label(field.name)}
            value={text(value)}
            disabled={!proposed}
            onChange={(e) => {
              set(field.name)(e.target.value);
            }}
          >
            {/* Left for the user to choose (F21.10.2): nothing is picked for them. */}
            {text(value) === "" && (
              <option value="" disabled>
                {t("card.choose")}
              </option>
            )}
            {field.options.map((option) => (
              <option key={option} value={option}>
                {say(`card.options.${option}`)}
              </option>
            ))}
          </Select>
        );
      case "switch":
        // Sharing is offered only inside a household where the user may share (F12.8).
        if (field.name === "shared" && !householdStore.mayShare) return null;
        return (
          <Switch
            key={field.name}
            checked={value === true}
            disabled={!proposed}
            onChange={set(field.name)}
            label={label(field.name)}
          />
        );
      default:
        return (
          <Input
            key={field.name}
            label={label(field.name)}
            value={text(value)}
            maxLength={120}
            disabled={!proposed}
            onChange={(e) => {
              set(field.name)(e.target.value);
            }}
          />
        );
    }
  };

  return (
    <CardShell
      message={message}
      title={say(`card.kinds.${card.kind}`)}
      icon={iconOf(card.kind)}
      busy={busy}
      onApprove={approve}
      blocked={card.form.some(
        (f) => f.kind === "choice" && f.required && text(fields[f.name]) === "",
      )}
      done={
        <Link to={screenOf(card.kind)} className="self-end text-md font-bold text-primary">
          {t("card.openScreen")}
        </Link>
      }
    >
      {card.form.map(control)}
    </CardShell>
  );
});
