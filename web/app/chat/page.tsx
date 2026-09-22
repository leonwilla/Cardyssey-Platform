"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  AppShell,
} from "@/components/AppShell";

import type {
  User,
} from "@/lib/types";

type Message = {
  id: string;
  senderFriendCode: string;
  recipientFriendCode: string;
  body: string;
  createdAt: string;
  readAt?: string | null;
};

type Thread = {
  friendCode: string;
  displayName?: string | null;
  lastMessage?: Message | null;
  unreadCount: number;
};

function time(value: string) {
  return new Intl.DateTimeFormat(
    "de-DE",
    {
      dateStyle: "short",
      timeStyle: "short",
    }
  ).format(new Date(value));
}

export default function ChatPage() {
  const router = useRouter();

  const [user, setUser] =
    useState<User | null>(null);

  const [threads, setThreads] =
    useState<Thread[]>([]);

  const [selected, setSelected] =
    useState<string | null>(null);

  const [messages, setMessages] =
    useState<Message[]>([]);

  const [draft, setDraft] =
    useState("");

  const [status, setStatus] =
    useState<string | null>(null);

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

        setSelected((current) =>
          current ??
          loaded[0]?.friendCode ??
          null
        );
      }
    }, []);

  const loadMessages =
    useCallback(
      async (
        friendCode: string
      ) => {
        const response =
          await fetch(
            `/api/chat/${
              encodeURIComponent(
                friendCode
              )
            }/messages`,
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

  useEffect(() => {
    const initialFriend =
      new URLSearchParams(
        window.location.search
      ).get("friend");

    if (initialFriend) {
      setSelected(initialFriend);
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
        if (loaded) setUser(loaded);
      });

    void loadThreads();
  }, [loadThreads, router]);

  useEffect(() => {
    if (!selected) return;

    void loadMessages(selected);

    const interval =
      window.setInterval(
        () => {
          void loadMessages(selected);
        },
        5000
      );

    return () =>
      window.clearInterval(interval);
  }, [loadMessages, selected]);

  async function send(
    event: FormEvent
  ) {
    event.preventDefault();

    if (
      !selected ||
      !draft.trim()
    ) {
      return;
    }

    const response =
      await fetch(
        `/api/chat/${
          encodeURIComponent(selected)
        }/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            body: draft,
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
    await loadMessages(selected);
  }

  async function report(
    message: Message
  ) {
    const reason =
      window.prompt(
        "Warum möchtest du diese Nachricht melden?",
        "Unangemessener Inhalt"
      );

    if (reason === null) return;

    const response =
      await fetch(
        `/api/chat/messages/${
          encodeURIComponent(message.id)
        }/report`,
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

  const activeThread =
    threads.find(
      (thread) =>
        thread.friendCode === selected
    );

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

          <h1>Freundeschat</h1>

          <p>
            Private Nachrichten sind nur
            zwischen bestätigten Freunden
            möglich.
          </p>
        </div>
      </section>

      <div className="chatLayout">
        <aside className="chatThreadList">
          <div className="chatListHead">
            <strong>Freunde</strong>
            <span>
              {threads.length}
            </span>
          </div>

          {threads.length === 0 ? (
            <p className="muted">
              Füge zuerst einen Freund hinzu,
              um einen Chat zu beginnen.
            </p>
          ) : (
            threads.map((thread) => (
              <button
                type="button"
                key={thread.friendCode}
                className={
                  selected ===
                  thread.friendCode
                    ? "chatThread active"
                    : "chatThread"
                }
                onClick={() =>
                  setSelected(
                    thread.friendCode
                  )
                }
              >
                <span className="chatAvatar">
                  {(thread.displayName ??
                    thread.friendCode)
                    .charAt(0)
                    .toUpperCase()}
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

          <div
            className="globalChatPreview"
            aria-disabled="true"
          >
            <span>Global · Vorschau</span>
            <strong>
              Cardyssey Lounge
            </strong>
            <small>
              Die globale Community-Umgebung ist
              vorbereitet. Schreiben bleibt
              gesperrt, bis die Schutzfunktionen
              vollständig aktiv sind.
            </small>
            <div className="globalChatSafety">
              <b>Melden</b>
              <b>Blockieren</b>
              <b>Spam-Schutz</b>
            </div>
            <button type="button" disabled>
              Lounge noch geschlossen
            </button>
          </div>
        </aside>

        <section className="chatRoom">
          {!selected ? (
            <div className="chatEmpty">
              Wähle einen Freund aus.
            </div>
          ) : (
            <>
              <header className="chatRoomHead">
                <div>
                  <span>
                    Privater Freundeschat
                  </span>
                  <strong>
                    {activeThread
                      ?.displayName ??
                      selected}
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
                        <p>{message.body}</p>
                        <footer>
                          <time>
                            {time(
                              message.createdAt
                            )}
                          </time>
                          <button
                            type="button"
                            onClick={() =>
                              report(message)
                            }
                          >
                            Melden
                          </button>
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
