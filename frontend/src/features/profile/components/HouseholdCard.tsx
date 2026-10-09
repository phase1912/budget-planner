import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { Check, Copy, RefreshCw } from "lucide-react";

import { Button } from "@/shared/components/Button/Button";
import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { Input } from "@/shared/components/Input/Input";
import { Pill } from "@/shared/components";
import type { HouseholdMember } from "@/stores/HouseholdStore";
import { useStores } from "@/stores/StoreContext";

/**
 * The user's household on Profile (E12 — F12.2, ADR-0017): start one, see who is in it,
 * and — as its owner — rename it and remove members, or leave it as a member. Every
 * action that takes someone out is confirmed first, because their access ends at once.
 *
 * It sits inside Profile's preferences form, so it has no form of its own: Enter in its
 * name field is handled here rather than submitting the preferences.
 */
export const HouseholdCard = observer(function HouseholdCard() {
  const { householdStore } = useStores();

  useEffect(() => {
    void householdStore.load();
  }, [householdStore]);

  return (
    <Card variant="surface" flush>
      <CardHeader>Household</CardHeader>
      <CardBody className="flex flex-col gap-4">
        {!householdStore.loaded ? (
          <p className="m-0 text-md text-muted-foreground">Loading…</p>
        ) : householdStore.household ? (
          <HouseholdDetails />
        ) : (
          <StartHousehold />
        )}
      </CardBody>
    </Card>
  );
});

const StartHousehold = observer(function StartHousehold() {
  const { householdStore } = useStores();
  const [name, setName] = useState("");
  const create = () => {
    if (name.trim()) void householdStore.create(name.trim());
  };

  return (
    <>
      <p className="m-0 text-md leading-relaxed text-muted-foreground">
        Keep one budget with your partner or family. Members see each other&apos;s receipts, except
        the ones marked private, and only the person who added a receipt can change it.
      </p>
      <div className="flex flex-col gap-2 md:flex-row md:items-end">
        <Input
          label="Household name"
          value={name}
          maxLength={60}
          placeholder="Home"
          containerClassName="w-full md:flex-1"
          onChange={(e) => {
            setName(e.target.value);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              create();
            }
          }}
        />
        <Button
          type="button"
          variant="primary"
          className="min-h-11 w-full md:w-auto"
          disabled={!name.trim() || householdStore.saveState.isLoading}
          onClick={create}
        >
          Create household
        </Button>
      </div>
    </>
  );
});

const HouseholdDetails = observer(function HouseholdDetails() {
  const { householdStore, authStore } = useStores();
  const household = householdStore.household;
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState("");
  const [confirmingLeave, setConfirmingLeave] = useState(false);
  if (!household) return null;

  const others = household.members.length - 1;
  const busy = householdStore.saveState.isLoading;
  const saveName = async () => {
    if (name.trim() && (await householdStore.rename(name.trim()))) setRenaming(false);
  };

  return (
    <>
      {renaming ? (
        <div className="flex flex-col gap-2 md:flex-row md:items-end">
          <Input
            label="Household name"
            value={name}
            maxLength={60}
            containerClassName="w-full md:flex-1"
            onChange={(e) => {
              setName(e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void saveName();
              }
            }}
          />
          <div className="flex flex-col gap-2 md:flex-row">
            <Button
              type="button"
              variant="ghost"
              className="min-h-11 w-full md:w-auto"
              onClick={() => {
                setRenaming(false);
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              className="min-h-11 w-full md:w-auto"
              disabled={!name.trim() || busy}
              onClick={() => void saveName()}
            >
              Save name
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <h3 className="m-0 break-words text-lg font-semibold text-foreground">
            {household.name}
          </h3>
          {householdStore.isOwner && (
            <Button
              type="button"
              variant="ghost"
              className="min-h-11 w-full md:min-h-0 md:w-auto"
              onClick={() => {
                setName(household.name);
                setRenaming(true);
              }}
            >
              Rename
            </Button>
          )}
        </div>
      )}

      <ul className="m-0 flex list-none flex-col divide-y divide-border rounded-control border border-border p-0">
        {household.members.map((member) => (
          <MemberRow
            key={member.user_id}
            member={member}
            isMe={member.user_id === authStore.user?.id}
          />
        ))}
      </ul>

      {householdStore.isOwner && <InviteLink />}

      {householdStore.isOwner && others > 0 ? (
        <p className="m-0 text-md text-muted-foreground">
          To leave, remove the other members first: a household needs its owner.
        </p>
      ) : confirmingLeave ? (
        <Confirm
          label="Leave household"
          question={
            others === 0
              ? "You are the only member, so the household will be deleted. Your receipts stay yours."
              : "You will no longer see the household's receipts, and it will no longer see yours."
          }
          action={others === 0 ? "Delete household" : "Leave"}
          busy={busy}
          onCancel={() => {
            setConfirmingLeave(false);
          }}
          onConfirm={() => void householdStore.leave()}
        />
      ) : (
        <Button
          type="button"
          variant="ghost"
          className="min-h-11 w-full md:min-h-0 md:w-auto md:self-start"
          onClick={() => {
            setConfirmingLeave(true);
          }}
        >
          {others === 0 ? "Delete household" : "Leave household"}
        </Button>
      )}
    </>
  );
});

/**
 * The owner's invite link (F12.3): sent however they like, it lets someone join after
 * seeing whose household it is. Replacing it is confirmed, since the old one dies at once.
 */
const InviteLink = observer(function InviteLink() {
  const { householdStore } = useStores();
  const [copied, setCopied] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const link = householdStore.inviteLink(window.location.origin) ?? "";

  const copy = async () => {
    await navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => {
      setCopied(false);
    }, 2000);
  };
  const regenerate = async () => {
    if (await householdStore.regenerateInvite()) setConfirming(false);
  };

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="household-invite" className="font-semibold text-foreground">
        Invite link
      </label>
      <p className="m-0 text-md leading-relaxed text-muted-foreground">
        Send it to the person you want to share a budget with. Anyone with the link can ask to join,
        so get a new one if it reaches someone else.
      </p>
      <div className="flex flex-col gap-2 md:flex-row md:items-center">
        <output
          id="household-invite"
          className="min-h-11 min-w-0 flex-1 break-all rounded-control border border-border bg-muted px-3 py-2.5 font-mono text-md text-foreground md:min-h-0"
        >
          {link}
        </output>
        <Button
          type="button"
          variant="secondary"
          className="min-h-11 w-full md:min-h-0 md:w-auto"
          onClick={() => void copy()}
        >
          {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
          {copied ? "Copied" : "Copy link"}
        </Button>
      </div>
      {confirming ? (
        <Confirm
          label="Replace invite link"
          question="The current link stops working at once. Members already in stay."
          action="Get a new link"
          busy={householdStore.saveState.isLoading}
          onCancel={() => {
            setConfirming(false);
          }}
          onConfirm={() => void regenerate()}
        />
      ) : (
        <Button
          type="button"
          variant="ghost"
          className="min-h-11 w-full md:min-h-0 md:w-auto md:self-start"
          onClick={() => {
            setConfirming(true);
          }}
        >
          <RefreshCw size={16} aria-hidden="true" />
          Get a new link
        </Button>
      )}
    </div>
  );
});

const MemberRow = observer(function MemberRow({
  member,
  isMe,
}: {
  member: HouseholdMember;
  isMe: boolean;
}) {
  const { householdStore } = useStores();
  const [confirming, setConfirming] = useState(false);
  const fullName = `${member.first_name} ${member.last_name}`.trim();

  return (
    <li className="flex flex-col gap-3 p-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="flex flex-wrap items-center gap-2 font-semibold text-foreground">
            {fullName}
            {member.role === "owner" && (
              <Pill size="sm" tone="success">
                Owner
              </Pill>
            )}
            {isMe && <Pill size="sm">You</Pill>}
          </span>
          <span className="break-all text-md text-muted-foreground">{member.email}</span>
        </div>
        {householdStore.isOwner && !isMe && !confirming && (
          <Button
            type="button"
            variant="ghost"
            className="min-h-11 w-full md:min-h-0 md:w-auto"
            onClick={() => {
              setConfirming(true);
            }}
          >
            Remove
          </Button>
        )}
      </div>
      {confirming && (
        <Confirm
          label={`Remove ${fullName}`}
          question={`${fullName} will no longer see the household's receipts, and it will no longer see theirs.`}
          action="Remove"
          busy={householdStore.saveState.isLoading}
          onCancel={() => {
            setConfirming(false);
          }}
          onConfirm={() => void householdStore.removeMember(member.user_id)}
        />
      )}
    </li>
  );
});

function Confirm({
  label,
  question,
  action,
  busy,
  onCancel,
  onConfirm,
}: {
  label: string;
  question: string;
  action: string;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      role="alertdialog"
      aria-label={label}
      className="flex flex-col gap-3 rounded-control border border-border p-3 md:flex-row md:items-center md:justify-between"
    >
      <p className="m-0 text-md text-foreground">{question}</p>
      <div className="flex flex-col gap-2 md:flex-row">
        <Button
          type="button"
          variant="ghost"
          className="min-h-11 w-full md:min-h-0 md:w-auto"
          onClick={onCancel}
        >
          Cancel
        </Button>
        <Button
          type="button"
          variant="danger"
          className="min-h-11 w-full md:min-h-0 md:w-auto"
          disabled={busy}
          onClick={onConfirm}
        >
          {action}
        </Button>
      </div>
    </div>
  );
}
