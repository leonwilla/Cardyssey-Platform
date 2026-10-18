"use client";

import {
  FormEvent,
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

type AdminMessage = {
  id: string;
  senderFriendCode: string;
  senderDisplayName?: string | null;
  recipientFriendCode: string;
  recipientDisplayName?: string | null;
  body: string;
  createdAt: string;
  readAt?: string | null;
};

type Report = {
  id: string;
  message: AdminMessage;
  reporterFriendCode: string;
  reporterDisplayName?: string | null;
  reason?: string | null;
  status: string;
  createdAt: string;
};

export default function AdminChatPage() {
  const router = useRouter();

  const [user, setUser] =
    useState<User | null>(null);

  const [reports, setReports] =
    useState<Report[]>([]);

  const [messages, setMessages] =
    useState<AdminMessage[]>([]);

  const [query, setQuery] =
    useState("");

  const [error, setError] =
    useState<string | null>(null);

  async function initialize() {
    const me =
      await fetch(
        "/api/auth/me",
        { cache: "no-store" }
      );

    if (me.status === 401) {
      router.replace("/login");
      return;
    }

    const loaded =
      await me.json() as User;

    if (
      loaded.canAdmin !== true &&
      loaded.role !== "ADMIN" &&
      loaded.role !== "FOUNDER"
    ) {
      router.replace("/account");
      return;
    }

    setUser(loaded);

    const response =
      await fetch(
        "/api/admin/chat/reports",
        { cache: "no-store" }
      );

    if (response.ok) {
      setReports(
        await response.json()
      );
    }
  }

  useEffect(() => {
    void Promise.resolve().then(initialize);
  }, []);

  async function search(
    event: FormEvent
  ) {
    event.preventDefault();
    setError(null);

    const response =
      await fetch(
        `/api/admin/chat/messages?q=${
          encodeURIComponent(query)
        }`,
        { cache: "no-store" }
      );

    if (!response.ok) {
      setError(
        "Nachrichten konnten nicht geladen werden."
      );
      return;
    }

    setMessages(
      await response.json()
    );
  }

  function messageCard(
    message: AdminMessage
  ) {
    return (
      <article
        className="adminChatMessage"
        key={message.id}
      >
        <div>
          <strong>
            {message.senderDisplayName ??
              message.senderFriendCode}
          </strong>
          <span>→</span>
          <strong>
            {message.recipientDisplayName ??
              message.recipientFriendCode}
          </strong>
        </div>

        <p>{message.body}</p>

        <small>
          {new Date(
            message.createdAt
          ).toLocaleString("de-DE")}
        </small>
      </article>
    );
  }

  return (
    <AppShell
      active="/admin/chat"
      user={user}
    >
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">
            Control Center
          </span>
          <h1>Chat-Moderation</h1>
          <p>
            Meldungen prüfen und bei Bedarf
            nach Nutzer oder Cardyssey-ID
            suchen. Jeder Zugriff wird
            protokolliert.
          </p>
        </div>
      </section>

      <section className="adminChatSection">
        <h2>
          Offene Meldungen
        </h2>

        {reports.length === 0 ? (
          <p className="muted">
            Keine gemeldeten Nachrichten.
          </p>
        ) : (
          reports.map((report) => (
            <div
              className="adminReportCard"
              key={report.id}
            >
              <div className="adminReportMeta">
                <strong>
                  Gemeldet von{" "}
                  {report.reporterDisplayName ??
                    report.reporterFriendCode}
                </strong>
                <span>
                  {report.reason ??
                    "Kein Grund angegeben"}
                </span>
              </div>
              {messageCard(
                report.message
              )}
            </div>
          ))
        )}
      </section>

      <section className="adminChatSection">
        <h2>
          Nachrichten durchsuchen
        </h2>

        <form
          className="adminChatSearch"
          onSubmit={search}
        >
          <input
            value={query}
            placeholder="Name, E-Mail, CDY-ID oder Nachricht …"
            onChange={(event) =>
              setQuery(
                event.target.value
              )
            }
          />
          <button
            className="primaryButton"
            type="submit"
          >
            Suchen
          </button>
        </form>

        {error && (
          <div className="statusPanel errorPanel">
            {error}
          </div>
        )}

        <div className="adminChatResults">
          {messages.map(messageCard)}
        </div>
      </section>
    </AppShell>
  );
}
