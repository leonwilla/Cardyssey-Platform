"use client";

import { SharedChatCard } from "@/components/SharedChatCard";

import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  AppShell,
} from "@/components/AppShell";

import type {
  PortfolioItem,
  User,
} from "@/lib/types";

type Message = {
  id: string;
  senderFriendCode: string;
  recipientFriendCode: string;
  body: string;
  objectType?: string | null;
  objectPayload?: unknown;
  replyToMessageId?: string | null;
  replyToSenderFriendCode?: string | null;
  replyToBody?: string | null;
  reactions?: ChatReaction[];
  createdAt: string;
  readAt?: string | null;
};

type Thread = {
  friendCode: string;
  displayName?: string | null;
  lastMessage?: Message | null;
  unreadCount: number;
};

type GroupMessage = {
  id: string;
  senderFriendCode: string;
  senderDisplayName?: string | null;
  body: string;
  objectType?: string | null;
  objectPayload?: unknown;
  replyToMessageId?: string | null;
  replyToSenderFriendCode?: string | null;
  replyToBody?: string | null;
  reactions?: ChatReaction[];
  createdAt: string;
};

type GroupSummary = {
  id: string;
  name: string;
  imageUrl?: string | null;
  memberCount: number;
  role: string;
  lastMessage?: GroupMessage | null;
  unreadCount: number;
};

type GroupMember = {
  friendCode: string;
  displayName?: string | null;
  role: string;
};

type GroupDetail = {
  id: string;
  name: string;
  imageUrl?: string | null;
  role: string;
  members: GroupMember[];
};

type ChatReaction = {
  emoji: string;
  count: number;
  reactedByMe: boolean;
};

type CommunityMessage = {
  id: string;
  roomId: string;
  senderFriendCode: string;
  senderDisplayName?: string | null;
  body: string;
  objectType?: string | null;
  objectPayload?: unknown;
  replyToMessageId?: string | null;
  replyToSenderFriendCode?: string | null;
  replyToBody?: string | null;
  reactions?: ChatReaction[];
  deleted?: boolean;
  createdAt: string;
};

type CommunityRoom = {
  id: string;
  slug: string;
  name: string;
  roomType: string;
  languageCode: string;
  setId?: string | null;
  setName?: string | null;
  unreadCount: number;
  lastActivityAt?: string | null;
  lastMessagePreview?: string | null;
  lastSenderDisplayName?: string | null;
};

type ChatSelection =
  | {
      kind: "friend";
      id: string;
    }
  | {
      kind: "group";
      id: string;
    }
  | {
      kind: "community";
      id: string;
    };

function groupImageSrc(
  value?: string | null
) {
  if (!value) return null;

  const prefix =
    "/api/v1/chat/group-images/";

  if (value.startsWith(prefix)) {
    return value.replace(
      prefix,
      "/api/chat/group-images/"
    );
  }

  return value;
}

function time(value: string) {
  return new Intl.DateTimeFormat(
    "de-DE",
    {
      dateStyle: "short",
      timeStyle: "short",
    }
  ).format(new Date(value));
}

function initials(value?: string | null) {
  return (value || "?")
    .trim()
    .charAt(0)
    .toUpperCase();
}

export default function ChatPage() {
  const router = useRouter();
  const imageInputRef =
    useRef<HTMLInputElement | null>(null);

  const [user, setUser] =
    useState<User | null>(null);

  const [threads, setThreads] =
    useState<Thread[]>([]);

  const [groups, setGroups] =
    useState<GroupSummary[]>([]);

  const [rooms, setRooms] =
    useState<CommunityRoom[]>([]);
  const [showCommunityDirectory,setShowCommunityDirectory]=useState(false);
  const [joinedRoomIds,setJoinedRoomIds]=useState<string[]>([]);
  const [roomSearch,setRoomSearch]=useState("");
  useEffect(()=>{try{const stored=JSON.parse(window.localStorage.getItem("cardyssey.chat.joinedRooms")||"[]");if(Array.isArray(stored))setJoinedRoomIds(stored.filter((x):x is string=>typeof x==="string"))}catch{}},[]);
  function toggleJoinedRoom(id:string){setJoinedRoomIds(prev=>{const next=prev.includes(id)?prev.filter(x=>x!==id):[...prev,id];window.localStorage.setItem("cardyssey.chat.joinedRooms",JSON.stringify(next));return next})}


  const [selection, setSelection] =
    useState<ChatSelection | null>(null);

  const [messages, setMessages] =
    useState<Message[]>([]);

  const [groupMessages, setGroupMessages] =
    useState<GroupMessage[]>([]);

  const [communityMessages, setCommunityMessages] =
    useState<CommunityMessage[]>([]);

  const [groupDetail, setGroupDetail] =
    useState<GroupDetail | null>(null);

  const [draft, setDraft] =
    useState("");

  const [status, setStatus] =
    useState<string | null>(null);

  const [showGroupSettings, setShowGroupSettings] =
    useState(false);

  const [replyingTo, setReplyingTo] =
    useState<{
      id: string;
      sender: string;
      body: string;
    } | null>(null);

  const [pendingShare, setPendingShare] = useState<PortfolioItem | null>(null);
  const [shareSending, setShareSending] = useState(false);

  const [shareOpen, setShareOpen] =
    useState(false);

  const [shareLoading, setShareLoading] =
    useState(false);

  const [shareCards, setShareCards] =
    useState<PortfolioItem[]>([]);
  const [shareQuery,setShareQuery]=useState("");
  const [shareSet,setShareSet]=useState("");

  const loadThreads =
    useCallback(async () => {
      const response =
        await fetch(
          "/api/chat/threads",
          { cache: "no-store" }
        );

      if (response.ok) {
        const loaded: Thread[] =
          await response.json();

        setThreads(loaded);
      }
    }, []);

  const loadGroups =
    useCallback(async () => {
      const response =
        await fetch(
          "/api/chat/groups",
          { cache: "no-store" }
        );

      if (response.ok) {
        const loaded =
          await response.json() as GroupSummary[];

        setGroups(loaded);
      }
    }, []);

  const loadRooms =
    useCallback(async () => {
      const response =
        await fetch(
          "/api/chat/community/rooms",
          { cache: "no-store" }
        );

      if (response.ok) {
        setRooms(
          await response.json()
        );
      }
    }, []);

  const loadFriendMessages =
    useCallback(
      async (friendCode: string) => {
        const response =
          await fetch(
            `/api/chat/${encodeURIComponent(friendCode)}/messages`,
            { cache: "no-store" }
          );

        if (response.ok) {
          setMessages(
            await response.json()
          );
          setStatus(null);
          void loadThreads();
        }
      },
      [loadThreads]
    );

  const loadGroupDetail =
    useCallback(
      async (groupId: string) => {
        const response =
          await fetch(
            `/api/chat/groups/${encodeURIComponent(groupId)}`,
            { cache: "no-store" }
          );

        if (response.ok) {
          setGroupDetail(
            await response.json()
          );
        }
      },
      []
    );

  const loadGroupMessages =
    useCallback(
      async (groupId: string) => {
        const response =
          await fetch(
            `/api/chat/groups/${encodeURIComponent(groupId)}/messages?limit=80`,
            { cache: "no-store" }
          );

        if (response.ok) {
          setGroupMessages(
            await response.json()
          );
          setStatus(null);
          void loadGroups();
        }
      },
      [loadGroups]
    );

  const loadCommunityMessages =
    useCallback(
      async (roomId: string) => {
        const response =
          await fetch(
            `/api/chat/community/rooms/${encodeURIComponent(roomId)}/messages?limit=80`,
            { cache: "no-store" }
          );

        if (response.ok) {
          setCommunityMessages(
            await response.json()
          );
          setStatus(null);
          void loadRooms();
        }
      },
      [loadRooms]
    );

  useEffect(() => {
    const initialFriend =
      new URLSearchParams(
        window.location.search
      ).get("friend");

    if (initialFriend) {
      setSelection({
        kind: "friend",
        id: initialFriend,
      });
    }

    fetch("/api/auth/me", {
      cache: "no-store",
    })
      .then(async (response) => {
        if (response.status === 401) {
          router.replace("/login");
          return null;
        }

        return response.ok
          ? response.json()
          : null;
      })
      .then((loaded) => {
        if (loaded) {
          setUser(loaded);
        }
      });

    void loadThreads();
    void loadGroups();
    void loadRooms();
  }, [
    loadGroups,
    loadRooms,
    loadThreads,
    router,
  ]);

  useEffect(() => {
    if (selection) {
      return;
    }

    if (groups.length > 0) {
      setSelection({
        kind: "group",
        id: groups[0].id,
      });
      return;
    }

    if (threads.length > 0) {
      setSelection({
        kind: "friend",
        id: threads[0].friendCode,
      });
    }
  }, [
    groups,
    selection,
    threads,
  ]);

  useEffect(() => {
    if (!selection) {
      return;
    }

    setShowGroupSettings(false);
    setDraft("");
    setReplyingTo(null);
    setShareOpen(false);

    if (selection.kind === "friend") {
      setGroupDetail(null);
      void loadFriendMessages(selection.id);

      const interval =
        window.setInterval(
          () => {
            void loadFriendMessages(selection.id);
          },
          5000
        );

      return () =>
        window.clearInterval(interval);
    }

    if (selection.kind === "group") {
      void loadGroupMessages(selection.id);
      void loadGroupDetail(selection.id);

      const interval =
        window.setInterval(
          () => {
            void loadGroupMessages(selection.id);
            void loadGroupDetail(selection.id);
          },
          5000
        );

      return () =>
        window.clearInterval(interval);
    }

    setGroupDetail(null);
    void loadCommunityMessages(selection.id);

    const interval =
      window.setInterval(
        () => {
          void loadCommunityMessages(selection.id);
        },
        5000
      );

    return () =>
      window.clearInterval(interval);
  }, [
    loadCommunityMessages,
    loadFriendMessages,
    loadGroupDetail,
    loadGroupMessages,
    selection,
  ]);

  async function send(
    event: FormEvent
  ) {
    event.preventDefault();

    if (
      !selection ||
      !draft.trim()
    ) {
      return;
    }

    const response =
      selection.kind === "friend"
        ? await fetch(
            `/api/chat/${encodeURIComponent(selection.id)}/messages`,
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json",
              },
              body: JSON.stringify({
                body: draft,
                replyToMessageId:
                  replyingTo?.id ?? null,
              }),
            }
          )
        : selection.kind === "group"
          ? await fetch(
              `/api/chat/groups/${encodeURIComponent(selection.id)}/messages`,
              {
                method: "POST",
                headers: {
                  "Content-Type":
                    "application/json",
                },
                body: JSON.stringify({
                  body: draft,
                  replyToMessageId:
                    replyingTo?.id ?? null,
                }),
              }
            )
          : await fetch(
              `/api/chat/community/rooms/${encodeURIComponent(selection.id)}/messages`,
              {
                method: "POST",
                headers: {
                  "Content-Type":
                    "application/json",
                },
                body: JSON.stringify({
                  body: draft,
                  replyToMessageId:
                    replyingTo?.id ?? null,
                }),
              }
            );

    if (!response.ok) {
      setStatus(
        "Nachricht konnte nicht gesendet werden."
      );
      return;
    }

    setDraft("");
    setReplyingTo(null);

    if (selection.kind === "friend") {
      await loadFriendMessages(
        selection.id
      );
    } else if (selection.kind === "group") {
      await loadGroupMessages(
        selection.id
      );
    } else {
      await loadCommunityMessages(
        selection.id
      );
    }
  }

  async function report(
    message: Message
  ) {
    const reason =
      window.prompt(
        "Warum möchtest du diese Nachricht melden?",
        "Unangemessener Inhalt"
      );

    if (reason === null) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/messages/${encodeURIComponent(message.id)}/report`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            reason,
          }),
        }
      );

    setStatus(
      response.ok
        ? "Nachricht wurde an die Moderation gemeldet."
        : "Meldung konnte nicht gesendet werden."
    );
  }

  async function toggleDirectReaction(
    messageId: string,
    emoji: string
  ) {
    if (
      !selection ||
      selection.kind !== "friend"
    ) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/${encodeURIComponent(selection.id)}/messages/${encodeURIComponent(messageId)}/reactions`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            emoji,
          }),
        }
      );

    if (response.ok) {
      await loadFriendMessages(
        selection.id
      );
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const cardId = params.get("shareCard");
    const language = params.get("language") || "de";
    if (!cardId || !["de", "en", "ja", "ko", "zh-cn", "zh-tw"].includes(language)) return;
    const controller = new AbortController();
    async function loadShare() {
      try {
        const key = params.get("collectionKey");
        if (key) {
          const response = await fetch("/api/collection", { signal: controller.signal, cache: "no-store" });
          if (!response.ok) throw new Error("Sammlung konnte nicht geladen werden.");
          const items = await response.json() as PortfolioItem[];
          const item = items.find(item => item.key === key && item.cardId === cardId && item.languageCode === language);
          if (!item) throw new Error("Die Karte ist nicht mehr in deiner Sammlung.");
          if (!controller.signal.aborted) setPendingShare(item);
        } else {
          const response = await fetch(`/api/cards/${encodeURIComponent(cardId!)}?language=${encodeURIComponent(language)}`, { signal: controller.signal, cache: "no-store" });
          if (!response.ok) throw new Error("Karte konnte zum Teilen nicht geladen werden.");
          const card = await response.json();
          const variant = card.variants?.find((value: any) => value.id === params.get("variantId"));
          if (!controller.signal.aborted) setPendingShare({
            key: card.id + ":" + language, cardId: card.id, languageCode: language,
            name: card.name, setId: card.setId, setName: card.setName, localId: card.localId,
            imageBase: card.imageBase, variant: variant?.legacyVariant ?? "", variantSpec: variant,
            condition: "", quantity: 1, marketUnitEur: {},
          });
        }
      } catch (error) {
        if (!controller.signal.aborted) setStatus(error instanceof Error ? error.message : "Karte konnte nicht geladen werden.");
      }
    }
    void loadShare();
    return () => controller.abort();
  }, []);

  async function openSharePicker() {
    if (!selection) {
      return;
    }

    setShareLoading(true);
    setShareOpen(true);

    try {
      const response =
        await fetch(
          "/api/collection",
          { cache: "no-store" }
        );

      if (!response.ok) {
        throw new Error();
      }

      setShareCards(
        await response.json() as PortfolioItem[]
      );
    } catch {
      setStatus(
        "Sammlung konnte zum Teilen nicht geladen werden."
      );
      setShareOpen(false);
    } finally {
      setShareLoading(false);
    }
  }

  async function shareCard(
    item: PortfolioItem
  ) {
    if (!selection || shareSending) return;
    setShareSending(true);
    try {
    const payload = {
      cardId: item.cardId,
      name: item.name,
      setId: item.setId,
      setName: item.setName,
      localId: item.localId,
      imageUrl: item.imageBase,
      languageCode: item.languageCode,
      variant: item.variant,
      ...(item.condition ? { condition: item.condition } : {}),
      variantSpec: item.variantSpec,
      quantity: item.quantity,
    };

    const target =
      selection.kind === "friend"
        ? `/api/chat/${encodeURIComponent(selection.id)}/messages`
        : selection.kind === "group"
          ? `/api/chat/groups/${encodeURIComponent(selection.id)}/messages`
          : `/api/chat/community/rooms/${encodeURIComponent(selection.id)}/messages`;

    const response =
      await fetch(
        target,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            body: "",
            objectType: "CARD",
            objectPayload: payload,
            replyToMessageId:
              replyingTo?.id ?? null,
          }),
        }
      );

    if (!response.ok) {
      setStatus(
        "Karte konnte nicht geteilt werden."
      );
      return;
    }

    setShareOpen(false);
    setPendingShare(null);
    window.history.replaceState(null, "", "/chat");
    setReplyingTo(null);

    if (selection.kind === "friend") {
      await loadFriendMessages(
        selection.id
      );
    } else if (selection.kind === "group") {
      await loadGroupMessages(
        selection.id
      );
    } else {
      await loadCommunityMessages(
        selection.id
      );
    }
    } catch {
      setStatus("Karte konnte nicht geteilt werden. Bitte erneut versuchen.");
    } finally {
      setShareSending(false);
    }
  }

  async function createGroup() {
    const name =
      window.prompt(
        "Name der neuen Gruppe:",
        "Meine Gruppe"
      )
        ?.trim();

    if (!name) {
      return;
    }

    const memberInput =
      window.prompt(
        "Freundes-Codes der Mitglieder, durch Komma getrennt. Leer lassen geht auch.",
        ""
      );

    if (memberInput === null) {
      return;
    }

    const memberFriendCodes =
      memberInput
        .split(",")
        .map((value) =>
          value.trim()
        )
        .filter(Boolean);

    const response =
      await fetch(
        "/api/chat/groups",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            name,
            memberFriendCodes,
          }),
        }
      );

    if (!response.ok) {
      setStatus(
        "Gruppe konnte nicht erstellt werden. Prüfe die Freundes-Codes."
      );
      return;
    }

    const group =
      await response.json() as GroupSummary;

    await loadGroups();

    setSelection({
      kind: "group",
      id: group.id,
    });

    setStatus(
      "Gruppe wurde erstellt."
    );
  }

  async function renameGroup() {
    if (
      !selection ||
      selection.kind !== "group" ||
      !groupDetail
    ) {
      return;
    }

    const name =
      window.prompt(
        "Neuer Gruppenname:",
        groupDetail.name
      )
        ?.trim();

    if (!name) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/groups/${encodeURIComponent(selection.id)}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            name,
          }),
        }
      );

    setStatus(
      response.ok
        ? "Gruppenname geändert."
        : "Gruppenname konnte nicht geändert werden."
    );

    if (response.ok) {
      await Promise.all([
        loadGroups(),
        loadGroupDetail(selection.id),
      ]);
    }
  }

  async function addMember() {
    if (
      !selection ||
      selection.kind !== "group"
    ) {
      return;
    }

    const friendCode =
      window.prompt(
        "Freundes-Code hinzufügen:"
      )
        ?.trim();

    if (!friendCode) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/groups/${encodeURIComponent(selection.id)}/members`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            friendCode,
          }),
        }
      );

    setStatus(
      response.ok
        ? "Mitglied hinzugefügt."
        : "Mitglied konnte nicht hinzugefügt werden."
    );

    if (response.ok) {
      await Promise.all([
        loadGroups(),
        loadGroupDetail(selection.id),
      ]);
    }
  }

  async function updateRole(
    member: GroupMember,
    role: "ADMIN" | "MEMBER"
  ) {
    if (
      !selection ||
      selection.kind !== "group"
    ) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/groups/${encodeURIComponent(selection.id)}/members/${encodeURIComponent(member.friendCode)}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            role,
          }),
        }
      );

    if (!response.ok) {
      setStatus(
        "Rolle konnte nicht geändert werden."
      );
      return;
    }

    await loadGroupDetail(
      selection.id
    );
  }

  async function removeMember(
    member: GroupMember
  ) {
    if (
      !selection ||
      selection.kind !== "group"
    ) {
      return;
    }

    if (
      !window.confirm(
        `${member.displayName || member.friendCode} aus der Gruppe entfernen?`
      )
    ) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/groups/${encodeURIComponent(selection.id)}/members/${encodeURIComponent(member.friendCode)}`,
        {
          method: "DELETE",
        }
      );

    setStatus(
      response.ok
        ? "Mitglied entfernt."
        : "Mitglied konnte nicht entfernt werden."
    );

    if (response.ok) {
      await Promise.all([
        loadGroups(),
        loadGroupDetail(selection.id),
      ]);
    }
  }

  async function leaveGroup() {
    if (
      !selection ||
      selection.kind !== "group"
    ) {
      return;
    }

    if (
      !window.confirm(
        "Gruppe wirklich verlassen?"
      )
    ) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/groups/${encodeURIComponent(selection.id)}/leave`,
        {
          method: "DELETE",
        }
      );

    if (!response.ok) {
      setStatus(
        "Gruppe konnte nicht verlassen werden."
      );
      return;
    }

    setSelection(null);
    setGroupDetail(null);
    setGroupMessages([]);
    await loadGroups();
  }

  async function reportCommunityMessage(
    message: CommunityMessage
  ) {
    const reason =
      window.prompt(
        "Warum möchtest du diese Nachricht melden?",
        "Unangemessener Inhalt"
      );

    if (reason === null) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/community/messages/${encodeURIComponent(message.id)}/report`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            reason,
          }),
        }
      );

    setStatus(
      response.ok
        ? "Nachricht wurde gemeldet."
        : "Meldung konnte nicht gesendet werden."
    );
  }

  async function blockCommunityUser(
    friendCode: string
  ) {
    if (
      !window.confirm(
        `${friendCode} blockieren?`
      )
    ) {
      return;
    }

    const response =
      await fetch(
        "/api/chat/community/blocks",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            friendCode,
          }),
        }
      );

    setStatus(
      response.ok
        ? "Nutzer wurde blockiert."
        : "Nutzer konnte nicht blockiert werden."
    );

    if (
      response.ok &&
      selection?.kind === "community"
    ) {
      await loadCommunityMessages(
        selection.id
      );
    }
  }

  async function toggleCommunityReaction(
    messageId: string,
    emoji: string
  ) {
    if (
      !selection ||
      selection.kind !== "community"
    ) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/community/rooms/${encodeURIComponent(selection.id)}/messages/${encodeURIComponent(messageId)}/reactions`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            emoji,
          }),
        }
      );

    if (response.ok) {
      await loadCommunityMessages(
        selection.id
      );
    }
  }

  async function toggleGroupReaction(
    messageId: string,
    emoji: string
  ) {
    if (
      !selection ||
      selection.kind !== "group"
    ) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/groups/${encodeURIComponent(selection.id)}/messages/${encodeURIComponent(messageId)}/reactions`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            emoji,
          }),
        }
      );

    if (response.ok) {
      await loadGroupMessages(
        selection.id
      );
    }
  }

  async function uploadGroupImage(
    file: File
  ) {
    if (
      !selection ||
      selection.kind !== "group"
    ) {
      return;
    }

    if (
      file.size >
      5 * 1024 * 1024
    ) {
      setStatus(
        "Gruppenbild ist zu groß."
      );
      return;
    }

    const response =
      await fetch(
        `/api/chat/groups/${encodeURIComponent(selection.id)}/image`,
        {
          method: "PUT",
          headers: {
            "Content-Type":
              file.type ||
              "application/octet-stream",
          },
          body: file,
        }
      );

    setStatus(
      response.ok
        ? "Gruppenbild aktualisiert."
        : "Gruppenbild konnte nicht aktualisiert werden."
    );

    if (response.ok) {
      await Promise.all([
        loadGroups(),
        loadGroupDetail(selection.id),
      ]);
    }
  }

  const activeThread =
    useMemo(
      () =>
        selection?.kind === "friend"
          ? threads.find(
              (thread) =>
                thread.friendCode ===
                selection.id
            )
          : null,
      [
        selection,
        threads,
      ]
    );

  const activeGroup =
    useMemo(
      () =>
        selection?.kind === "group"
          ? groups.find(
              (group) =>
                group.id === selection.id
            )
          : null,
      [
        groups,
        selection,
      ]
    );

  const activeRoom =
    useMemo(
      () =>
        selection?.kind === "community"
          ? rooms.find(
              (room) =>
                room.id === selection.id
            )
          : null,
      [
        rooms,
        selection,
      ]
    );

  function ComposerExtras() {
    return (
      <>
        {replyingTo && (
          <div
            className="statusPanel"
            style={{
              margin: "0 12px 8px",
              padding: "10px 12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
            }}
          >
            <div>
              <strong>
                Antwort an {replyingTo.sender}
              </strong>
              <div className="muted">
                {replyingTo.body || "Geteilter Inhalt"}
              </div>
            </div>
            <button
              type="button"
              className="ghostButton"
              onClick={() =>
                setReplyingTo(null)
              }
            >
              Abbrechen
            </button>
          </div>
        )}

        {shareOpen && (
          <div
            className="statusPanel"
            style={{
              margin: "0 12px 8px",
              padding: "12px",
              maxHeight: "280px",
              overflowY: "auto",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "10px",
                marginBottom: "10px",
              }}
            >
              <strong>
                Karte aus deiner Sammlung teilen
              </strong>
              <button
                type="button"
                className="ghostButton"
                onClick={() =>
                  setShareOpen(false)
                }
              >
                Schließen
              </button>
            </div>

            <div className="chatShareFilters"><label>Set<select value={shareSet} onChange={e=>setShareSet(e.target.value)}><option value="">Alle Sets</option>{Array.from(new Set(shareCards.map(c=>c.setName||c.setId||"Unbekanntes Set"))).sort((a,b)=>a.localeCompare(b,"de")).map(name=><option key={name} value={name}>{name}</option>)}</select></label><label>Karte suchen<input value={shareQuery} onChange={e=>setShareQuery(e.target.value)} placeholder="Name, Nummer oder Variante …" /></label></div>
            {shareLoading ? (
              <div className="muted">
                Sammlung wird geladen …
              </div>
            ) : shareCards.length === 0 ? (
              <div className="muted">
                Keine Karten in der Sammlung.
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gap: "7px",
                }}
              >
                {shareCards.filter(item=>(!shareSet||(item.setName||item.setId||"Unbekanntes Set")===shareSet)&&([item.name,item.localId,item.cardId,item.variant].join(" ").toLowerCase().includes(shareQuery.toLowerCase()))).slice(0,90)
                  .map((item) => (
                    <button
                      type="button"
                      key={item.key}
                      disabled={shareSending}
                      className="chatThread"
                      onClick={() =>
                        void shareCard(item)
                      }
                      style={{
                        width: "100%",
                        textAlign: "left",
                      }}
                    >
                      {item.imageBase?<img className="chatShareThumb" src={item.imageBase.replace(/\/$/,"")+"/low.webp"} alt="" loading="lazy"/>:<span className="chatAvatar">{initials(item.name)}</span>}
                      <span className="chatThreadText">
                        <strong>
                          {item.name}
                        </strong>
                        <small>
                          {item.setName || item.setId || "—"} · {item.localId || item.cardId} · {item.languageCode.toUpperCase()} · {item.variant}
                        </small>
                      </span>
                      <b>
                        ×{item.quantity}
                      </b>
                    </button>
                  ))}
              </div>
            )}
          </div>
        )}
      </>
    );
  }

  return (
    <AppShell
      active="/chat"
      user={user}
    >
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">
            Nachrichten
          </span>

          <h1>Chats & Gruppen</h1>

          <p>
            Freundeschats und Gruppen laufen
            jetzt auf Web und Android über
            denselben Cardyssey-Stand.
          </p>
        </div>

        <button
          type="button"
          className="primaryButton"
          onClick={() =>
            void createGroup()
          }
        >
          + Neue Gruppe
        </button>
      </section>

      {pendingShare && (
        <div className="statusPanel">
          <strong>{pendingShare.name} teilen</strong>
          <p>{selection ? "Die Karte wird an den ausgewählten Chat gesendet." : "Wähle zuerst einen Freund, eine Gruppe oder einen Raum."}</p>
          <button className="primaryButton" disabled={!selection || shareSending} onClick={() => void shareCard(pendingShare)}>
            {shareSending ? "Wird gesendet …" : "Karte jetzt senden"}
          </button>
          <button className="ghostButton" disabled={shareSending} onClick={() => { setPendingShare(null); window.history.replaceState(null, "", "/chat"); }}>Abbrechen</button>
        </div>
      )}
      <div className="chatLayout">
        <aside className="chatThreadList">
          <div className="chatListHead">
            <strong>Gruppen</strong>
            <span>
              {groups.length}
            </span>
          </div>

          {groups.length === 0 ? (
            <p className="muted">
              Noch keine Gruppen.
            </p>
          ) : (
            groups.map((group) => (
              <button
                type="button"
                key={group.id}
                className={
                  selection?.kind === "group" &&
                  selection.id === group.id
                    ? "chatThread active"
                    : "chatThread"
                }
                onClick={() =>
                  setSelection({
                    kind: "group",
                    id: group.id,
                  })
                }
              >
                <span className="chatAvatar">
                  {group.imageUrl ? (
                    <img
                      src={groupImageSrc(group.imageUrl) ?? undefined}
                      alt=""
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        borderRadius: "inherit",
                      }}
                    />
                  ) : (
                    initials(group.name)
                  )}
                </span>

                <span className="chatThreadText">
                  <strong>
                    {group.name}
                  </strong>
                  <small>
                    {group.lastMessage
                      ?.body ||
                      `${group.memberCount} Mitglieder`}
                  </small>
                </span>

                {group.unreadCount > 0 && (
                  <b className="chatUnread">
                    {group.unreadCount}
                  </b>
                )}
              </button>
            ))
          )}

          <div className="chatListHead">
            <strong>Freunde</strong>
            <span>
              {threads.length}
            </span>
          </div>

          {threads.length === 0 ? (
            <p className="muted">
              Füge zuerst einen Freund hinzu,
              um einen privaten Chat zu beginnen.
            </p>
          ) : (
            threads.map((thread) => (
              <button
                type="button"
                key={thread.friendCode}
                className={
                  selection?.kind === "friend" &&
                  selection.id ===
                    thread.friendCode
                    ? "chatThread active"
                    : "chatThread"
                }
                onClick={() =>
                  setSelection({
                    kind: "friend",
                    id: thread.friendCode,
                  })
                }
              >
                <span className="chatAvatar">
                  {initials(
                    thread.displayName ??
                      thread.friendCode
                  )}
                </span>

                <span className="chatThreadText">
                  <strong>
                    {thread.displayName ??
                      "Cardyssey Collector"}
                  </strong>
                  <small>
                    {thread.lastMessage
                      ?.body ??
                      "Noch keine Nachricht"}
                  </small>
                </span>

                {thread.unreadCount > 0 && (
                  <b className="chatUnread">
                    {thread.unreadCount}
                  </b>
                )}
              </button>
            ))
          )}

          <div className="chatListHead"><strong>Meine Community-Räume</strong><span>{rooms.filter(r=>joinedRoomIds.includes(r.id)).length}</span></div>
          {rooms.filter(r=>joinedRoomIds.includes(r.id)).map(room=>(
            <div className="chatDirectoryRow" key={room.id}>
              <button
                type="button"
                key={room.id}
                className={
                  selection?.kind === "community" &&
                  selection.id === room.id
                    ? "chatThread active"
                    : "chatThread"
                }
                onClick={() => {setSelection({kind:"community",id:room.id});setShowCommunityDirectory(false)}}
              >
                <span className="chatAvatar">
                  #
                </span>

                <span className="chatThreadText">
                  <strong>
                    {room.name}
                  </strong>
                  <small>
                    {room.lastMessagePreview ??
                      (
                        room.roomType === "SET"
                          ? room.setName
                          : room.languageCode.toUpperCase()
                      ) ??
                      "Community"}
                  </small>
                </span>

                {room.unreadCount > 0 && (
                  <b className="chatUnread">
                    {room.unreadCount}
                  </b>
                )}
              </button>
              <button className="chatRoomJoin" title="Raum aus meiner Liste entfernen" onClick={()=>toggleJoinedRoom(room.id)}>−</button>
            </div>
          ))}
          <button type="button" className="chatBrowseRooms" onClick={()=>setShowCommunityDirectory(v=>!v)} aria-expanded={showCommunityDirectory}>
            {showCommunityDirectory?"Raumverzeichnis schließen":"+ Community-Räume entdecken"} <small>{rooms.length} verfügbar</small>
          </button>
          {showCommunityDirectory&&<div className="chatDirectory"><input type="search" value={roomSearch} onChange={e=>setRoomSearch(e.target.value)} placeholder="Sprache, Raum oder Set suchen" aria-label="Community-Räume durchsuchen" />
          {rooms.filter(room=>(room.name+" "+room.languageCode+" "+(room.setName||"")).toLowerCase().includes(roomSearch.toLowerCase())).slice(0,30).map(room=><div className="chatDirectoryRow" key={room.id}><button className="chatThread" onClick={()=>setSelection({kind:"community",id:room.id})}><span className="chatAvatar">#</span><span className="chatThreadText"><strong>{room.name}</strong><small>{room.languageCode.toUpperCase()}{room.setName?" · "+room.setName:""}</small></span></button><button className="chatRoomJoin" title={joinedRoomIds.includes(room.id)?"Entfernen":"Zu meinen Räumen hinzufügen"} onClick={()=>toggleJoinedRoom(room.id)}>{joinedRoomIds.includes(room.id)?"✓":"+"}</button></div>)}</div>}
        </aside>

        <section className="chatRoom">
          {!selection ? (
            <div className="chatEmpty">
              Wähle einen Chat oder eine Gruppe.
            </div>
          ) : selection.kind === "friend" ? (
            <>
              <header className="chatRoomHead">
                <div>
                  <span>
                    Privater Freundeschat
                  </span>
                  <strong>
                    {activeThread
                      ?.displayName ??
                      selection.id}
                  </strong>
                </div>
              </header>

              <div className="chatMessages">
                {messages.length === 0 ? (
                  <div className="chatEmpty">
                    Noch keine Nachrichten.
                  </div>
                ) : (
                  messages.map((message) => {
                    const own =
                      message.senderFriendCode ===
                      user?.friendCode;

                    return (
                      <article
                        key={message.id}
                        className={
                          own
                            ? "chatMessage own"
                            : "chatMessage"
                        }
                      >
                        {message.replyToMessageId && (
                          <div
                            className="muted"
                            style={{
                              borderLeft:
                                "2px solid var(--cyan)",
                              paddingLeft: "8px",
                              marginBottom: "6px",
                              fontSize: "12px",
                            }}
                          >
                            Antwort auf {message.replyToSenderFriendCode || "Nachricht"} · {message.replyToBody || "Geteilter Inhalt"}
                          </div>
                        )}

                        <p>
                          {message.body}
                        </p>

                        <SharedChatCard objectType={message.objectType} payload={message.objectPayload} />

                        <div
                          style={{
                            display: "flex",
                            gap: "5px",
                            flexWrap: "wrap",
                            marginTop: "7px",
                          }}
                        >
                          {["❤️", "👍", "🔥", "😂", "😮"].map(
                            (emoji) => {
                              const reaction =
                                message.reactions?.find(
                                  (item) =>
                                    item.emoji === emoji
                                );

                              return (
                                <button
                                  key={emoji}
                                  type="button"
                                  className="ghostButton"
                                  style={{
                                    minHeight: "30px",
                                    padding: "0 8px",
                                    opacity:
                                      reaction?.reactedByMe
                                        ? 1
                                        : 0.75,
                                  }}
                                  onClick={() =>
                                    void toggleDirectReaction(
                                      message.id,
                                      emoji
                                    )
                                  }
                                >
                                  {emoji}
                                  {reaction?.count
                                    ? ` ${reaction.count}`
                                    : ""}
                                </button>
                              );
                            }
                          )}
                        </div>

                        <footer>
                          <time>
                            {time(
                              message.createdAt
                            )}
                          </time>
                          <button
                            type="button"
                            onClick={() =>
                              setReplyingTo({
                                id: message.id,
                                sender:
                                  message.senderFriendCode,
                                body:
                                  message.body ||
                                  "Geteilter Inhalt",
                              })
                            }
                          >
                            Antworten
                          </button>
                          {!own && (
                            <button
                              type="button"
                              onClick={() =>
                                report(message)
                              }
                            >
                              Melden
                            </button>
                          )}
                        </footer>
                      </article>
                    );
                  })
                )}
              </div>

              {status && (
                <div className="chatStatus">
                  {status}
                </div>
              )}

              <ComposerExtras />

              <form
                className="chatComposer"
                onSubmit={send}
              >
                <textarea
                  value={draft}
                  maxLength={2000}
                  placeholder="Nachricht schreiben …"
                  onChange={(event) =>
                    setDraft(
                      event.target.value
                    )
                  }
                />

                <button
                  type="button"
                  className="ghostButton"
                  onClick={() =>
                    void openSharePicker()
                  }
                >
                  Karte teilen
                </button>

                <button
                  className="primaryButton"
                  type="submit"
                  disabled={!draft.trim()}
                >
                  Senden
                </button>
              </form>
            </>
          ) : selection.kind === "group" ? (
            <>
              <header className="chatRoomHead">
                <div
                  style={{
                    display: "flex",
                    gap: "12px",
                    alignItems: "center",
                  }}
                >
                  <span className="chatAvatar">
                    {activeGroup?.imageUrl ? (
                      <img
                        src={groupImageSrc(activeGroup.imageUrl) ?? undefined}
                        alt=""
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          borderRadius: "inherit",
                        }}
                      />
                    ) : (
                      initials(
                        activeGroup?.name
                      )
                    )}
                  </span>
                  <div>
                    <span>
                      Gruppe · {activeGroup?.memberCount ?? 0} Mitglieder
                    </span>
                    <strong>
                      {activeGroup?.name ??
                        groupDetail?.name ??
                        "Gruppe"}
                    </strong>
                  </div>
                </div>

                <button
                  type="button"
                  className="ghostButton"
                  onClick={() =>
                    setShowGroupSettings(
                      (current) =>
                        !current
                    )
                  }
                >
                  Verwalten
                </button>
              </header>

              {showGroupSettings && groupDetail && (
                <div
                  className="statusPanel"
                  style={{
                    margin: "12px",
                    display: "grid",
                    gap: "12px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      gap: "8px",
                      flexWrap: "wrap",
                    }}
                  >
                    {(groupDetail.role === "OWNER" ||
                      groupDetail.role === "ADMIN") && (
                      <>
                        <button
                          type="button"
                          className="ghostButton"
                          onClick={() =>
                            void renameGroup()
                          }
                        >
                          Namen ändern
                        </button>
                        <button
                          type="button"
                          className="ghostButton"
                          onClick={() =>
                            void addMember()
                          }
                        >
                          Freund hinzufügen
                        </button>
                        <button
                          type="button"
                          className="ghostButton"
                          onClick={() =>
                            imageInputRef.current?.click()
                          }
                        >
                          Gruppenbild
                        </button>
                        <input
                          ref={imageInputRef}
                          type="file"
                          accept="image/*"
                          hidden
                          onChange={(event) => {
                            const file =
                              event.target.files?.[0];

                            if (file) {
                              void uploadGroupImage(
                                file
                              );
                            }

                            event.currentTarget.value = "";
                          }}
                        />
                      </>
                    )}

                    <button
                      type="button"
                      className="ghostButton"
                      style={{
                        color: "var(--pink)",
                      }}
                      onClick={() =>
                        void leaveGroup()
                      }
                    >
                      Gruppe verlassen
                    </button>
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gap: "8px",
                    }}
                  >
                    {groupDetail.members.map(
                      (member) => (
                        <div
                          key={member.friendCode}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: "10px",
                            padding: "8px 0",
                            borderBottom:
                              "1px solid rgba(38,58,85,.45)",
                          }}
                        >
                          <div>
                            <strong>
                              {member.displayName ||
                                member.friendCode}
                            </strong>
                            <div className="muted">
                              {member.friendCode} · {member.role}
                            </div>
                          </div>

                          {groupDetail.role === "OWNER" &&
                            member.role !== "OWNER" && (
                              <div
                                style={{
                                  display: "flex",
                                  gap: "6px",
                                  flexWrap: "wrap",
                                }}
                              >
                                <button
                                  type="button"
                                  className="ghostButton"
                                  onClick={() =>
                                    void updateRole(
                                      member,
                                      member.role === "ADMIN"
                                        ? "MEMBER"
                                        : "ADMIN"
                                    )
                                  }
                                >
                                  {member.role === "ADMIN"
                                    ? "Admin entfernen"
                                    : "Zum Admin"}
                                </button>
                                <button
                                  type="button"
                                  className="ghostButton"
                                  onClick={() =>
                                    void removeMember(
                                      member
                                    )
                                  }
                                >
                                  Entfernen
                                </button>
                              </div>
                            )}

                          {groupDetail.role === "ADMIN" &&
                            member.role === "MEMBER" && (
                              <button
                                type="button"
                                className="ghostButton"
                                onClick={() =>
                                  void removeMember(
                                    member
                                  )
                                }
                              >
                                Entfernen
                              </button>
                            )}
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}

              <div className="chatMessages">
                {groupMessages.length === 0 ? (
                  <div className="chatEmpty">
                    Noch keine Gruppennachrichten.
                  </div>
                ) : (
                  groupMessages.map(
                    (message) => {
                      const own =
                        message.senderFriendCode ===
                        user?.friendCode;

                      return (
                        <article
                          key={message.id}
                          className={
                            own
                              ? "chatMessage own"
                              : "chatMessage"
                          }
                        >
                          {!own && (
                            <strong
                              style={{
                                fontSize: "12px",
                              }}
                            >
                              {message.senderDisplayName ||
                                message.senderFriendCode}
                            </strong>
                          )}

                          {message.replyToMessageId && (
                            <div
                              className="muted"
                              style={{
                                borderLeft:
                                  "2px solid var(--cyan)",
                                paddingLeft: "8px",
                                margin: "6px 0",
                                fontSize: "12px",
                              }}
                            >
                              Antwort auf {message.replyToSenderFriendCode || "Nachricht"} · {message.replyToBody || "Geteilter Inhalt"}
                            </div>
                          )}

                          <p>
                            {message.body}
                          </p>

                          <SharedChatCard objectType={message.objectType} payload={message.objectPayload} />

                          <div
                            style={{
                              display: "flex",
                              gap: "5px",
                              flexWrap: "wrap",
                              marginTop: "7px",
                            }}
                          >
                            {["❤️", "👍", "🔥", "😂", "😮"].map(
                              (emoji) => {
                                const reaction =
                                  message.reactions?.find(
                                    (item) =>
                                      item.emoji === emoji
                                  );

                                return (
                                  <button
                                    key={emoji}
                                    type="button"
                                    className="ghostButton"
                                    style={{
                                      minHeight: "30px",
                                      padding: "0 8px",
                                      opacity:
                                        reaction?.reactedByMe
                                          ? 1
                                          : 0.75,
                                    }}
                                    onClick={() =>
                                      void toggleGroupReaction(
                                        message.id,
                                        emoji
                                      )
                                    }
                                  >
                                    {emoji}
                                    {reaction?.count
                                      ? ` ${reaction.count}`
                                      : ""}
                                  </button>
                                );
                              }
                            )}
                          </div>

                          <footer>
                            <time>
                              {time(
                                message.createdAt
                              )}
                            </time>
                            <button
                              type="button"
                              onClick={() =>
                                setReplyingTo({
                                  id: message.id,
                                  sender:
                                    message.senderDisplayName ||
                                    message.senderFriendCode,
                                  body:
                                    message.body ||
                                    "Geteilter Inhalt",
                                })
                              }
                            >
                              Antworten
                            </button>
                          </footer>
                        </article>
                      );
                    }
                  )
                )}
              </div>

              {status && (
                <div className="chatStatus">
                  {status}
                </div>
              )}

              <ComposerExtras />

              <form
                className="chatComposer"
                onSubmit={send}
              >
                <textarea
                  value={draft}
                  maxLength={2000}
                  placeholder="Nachricht an die Gruppe …"
                  onChange={(event) =>
                    setDraft(
                      event.target.value
                    )
                  }
                />

                <button
                  type="button"
                  className="ghostButton"
                  onClick={() =>
                    void openSharePicker()
                  }
                >
                  Karte teilen
                </button>

                <button
                  className="primaryButton"
                  type="submit"
                  disabled={!draft.trim()}
                >
                  Senden
                </button>
              </form>
            </>
          ) : (
            <>
              <header className="chatRoomHead">
                <div>
                  <span>
                    Community · {activeRoom?.languageCode.toUpperCase() ?? "GLOBAL"}
                  </span>
                  <strong>
                    {activeRoom?.name ?? "Community"}
                  </strong>
                </div>
              </header>

              <div className="chatMessages">
                {communityMessages.length === 0 ? (
                  <div className="chatEmpty">
                    Noch keine Nachrichten in diesem Raum.
                  </div>
                ) : (
                  communityMessages.map(
                    (message) => {
                      const own =
                        message.senderFriendCode ===
                        user?.friendCode;

                      return (
                        <article
                          key={message.id}
                          className={
                            own
                              ? "chatMessage own"
                              : "chatMessage"
                          }
                        >
                          {!own && (
                            <strong
                              style={{
                                fontSize: "12px",
                              }}
                            >
                              {message.senderDisplayName ||
                                message.senderFriendCode}
                            </strong>
                          )}

                          {message.replyToMessageId && (
                            <div
                              className="muted"
                              style={{
                                borderLeft:
                                  "2px solid var(--cyan)",
                                paddingLeft: "8px",
                                margin: "6px 0",
                                fontSize: "12px",
                              }}
                            >
                              Antwort auf {message.replyToSenderFriendCode || "Nachricht"} · {message.replyToBody || "Geteilter Inhalt"}
                            </div>
                          )}

                          {message.deleted ? (
                            <p className="muted">
                              Nachricht entfernt.
                            </p>
                          ) : (
                            <p>{message.body}</p>
                          )}

                          <SharedChatCard objectType={message.objectType} payload={message.objectPayload} />

                          <div
                            style={{
                              display: "flex",
                              gap: "5px",
                              flexWrap: "wrap",
                              marginTop: "7px",
                            }}
                          >
                            {["❤️", "👍", "🔥", "😂", "😮"].map(
                              (emoji) => {
                                const reaction =
                                  message.reactions?.find(
                                    (item) =>
                                      item.emoji === emoji
                                  );

                                return (
                                  <button
                                    key={emoji}
                                    type="button"
                                    className="ghostButton"
                                    style={{
                                      minHeight: "30px",
                                      padding: "0 8px",
                                      opacity:
                                        reaction?.reactedByMe
                                          ? 1
                                          : 0.75,
                                    }}
                                    onClick={() =>
                                      void toggleCommunityReaction(
                                        message.id,
                                        emoji
                                      )
                                    }
                                  >
                                    {emoji}
                                    {reaction?.count
                                      ? ` ${reaction.count}`
                                      : ""}
                                  </button>
                                );
                              }
                            )}
                          </div>

                          <footer>
                            <time>
                              {time(
                                message.createdAt
                              )}
                            </time>

                            <button
                              type="button"
                              onClick={() =>
                                setReplyingTo({
                                  id: message.id,
                                  sender:
                                    message.senderDisplayName ||
                                    message.senderFriendCode,
                                  body:
                                    message.body ||
                                    "Geteilter Inhalt",
                                })
                              }
                            >
                              Antworten
                            </button>

                            {!own && (
                              <>
                                <button
                                  type="button"
                                  onClick={() =>
                                    void reportCommunityMessage(
                                      message
                                    )
                                  }
                                >
                                  Melden
                                </button>
                                <button
                                  type="button"
                                  onClick={() =>
                                    void blockCommunityUser(
                                      message.senderFriendCode
                                    )
                                  }
                                >
                                  Blockieren
                                </button>
                              </>
                            )}
                          </footer>
                        </article>
                      );
                    }
                  )
                )}
              </div>

              {status && (
                <div className="chatStatus">
                  {status}
                </div>
              )}

              <ComposerExtras />

              <form
                className="chatComposer"
                onSubmit={send}
              >
                <textarea
                  value={draft}
                  maxLength={2000}
                  placeholder="Nachricht an die Community …"
                  onChange={(event) =>
                    setDraft(
                      event.target.value
                    )
                  }
                />

                <button
                  type="button"
                  className="ghostButton"
                  onClick={() =>
                    void openSharePicker()
                  }
                >
                  Karte teilen
                </button>

                <button
                  className="primaryButton"
                  type="submit"
                  disabled={!draft.trim()}
                >
                  Senden
                </button>
              </form>
            </>
          )}
        </section>
      </div>
    </AppShell>
  );
}
