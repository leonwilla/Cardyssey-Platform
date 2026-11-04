"use client";

import {
  useEffect,
  useState,
} from "react";

import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import type { User } from "@/lib/types";

type FriendUser = {
  friendCode: string;
  displayName?: string | null;
};

type FriendRequest = {
  id: string;
  user: FriendUser;
  createdAt: string;
};

export default function FriendsPanel({embedded=false}:{embedded?:boolean}={}) {
  const router = useRouter();

  const [user, setUser] =
    useState<User | null>(null);

  const [friends, setFriends] =
    useState<FriendUser[]>([]);

  const [incoming, setIncoming] =
    useState<FriendRequest[]>([]);

  const [outgoing, setOutgoing] =
    useState<FriendRequest[]>([]);

  const [query, setQuery] =
    useState("");

  const [results, setResults] =
    useState<FriendUser[]>([]);

  const [message, setMessage] =
    useState<string | null>(null);

  async function loadFriends() {
    const [friendsResponse, requestsResponse] =
      await Promise.all([
        fetch("/api/friends", {
          cache: "no-store",
        }),
        fetch("/api/friends/requests", {
          cache: "no-store",
        }),
      ]);

    if (friendsResponse.ok) {
      setFriends(await friendsResponse.json());
    }

    if (requestsResponse.ok) {
      const data = await requestsResponse.json();

      setIncoming(data.incoming ?? []);
      setOutgoing(data.outgoing ?? []);
    }
  }

  useEffect(() => {
    async function load() {
      const me =
        await fetch("/api/auth/me", {
          cache: "no-store",
        });

      if (me.status === 401) {
        router.replace("/login");
        return;
      }

      if (me.ok) {
        setUser(await me.json());
      }

      await loadFriends();
    }

    load();
  }, [router]);

  async function search() {
    const q = query.trim();

    if (q.length < 2) {
      setResults([]);
      return;
    }

    setMessage(null);

    const response =
      await fetch(
        `/api/friends/search?q=${encodeURIComponent(q)}`,
        { cache: "no-store" }
      );

    if (!response.ok) {
      setMessage("Suche fehlgeschlagen.");
      return;
    }

    setResults(await response.json());
  }

  async function sendRequest(
    friendCode: string
  ) {
    const response =
      await fetch("/api/friends/requests", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          friendCode,
        }),
      });

    if (response.status === 409) {
      setMessage(
        "Mit diesem Nutzer besteht bereits eine Verbindung oder Anfrage."
      );
      return;
    }

    if (!response.ok) {
      setMessage(
        "Freundschaftsanfrage konnte nicht gesendet werden."
      );
      return;
    }

    setMessage("Freundschaftsanfrage gesendet.");
    setResults([]);

    await loadFriends();
  }

  async function accept(id: string) {
    const response =
      await fetch(
        `/api/friends/requests/${encodeURIComponent(id)}/accept`,
        { method: "POST" }
      );

    if (response.ok) {
      await loadFriends();
    }
  }

  async function removeRequest(id: string) {
    const response =
      await fetch(
        `/api/friends/requests/${encodeURIComponent(id)}`,
        { method: "DELETE" }
      );

    if (response.ok) {
      await loadFriends();
    }
  }

  const content = (<>
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">
            Community
          </span>

          <h1>Sammler verbinden</h1>

          <p>
            Freunde, Sammlungen und
            gemeinsame Karten an einem Ort.
          </p>
        </div>
      </section>

      <section className="friendSection">
        <h2>Sammler finden</h2>

        <div className="friendSearchRow">
          <input
            value={query}
            placeholder="Name oder CDY-..."
            onChange={
              (e) =>
                setQuery(e.target.value)
            }
            onKeyDown={
              (e) => {
                if (e.key === "Enter") {
                  search();
                }
              }
            }
          />

          <button
            className="primaryButton"
            onClick={search}
          >
            Suchen
          </button>
        </div>

        {message && (
          <div className="statusPanel">
            {message}
          </div>
        )}

        {results.map((result) => (
          <div
            className="friendRow"
            key={result.friendCode}
          >
            <div>
              <strong>
                {result.displayName ??
                  "Cardyssey Collector"}
              </strong>

              <span>
                {result.friendCode}
              </span>
            </div>

            <div className="friendActions">
              <button
                className="ghostButton"
                onClick={
                  () =>
                    router.push(
                      `/friends/${
                        encodeURIComponent(
                          result.friendCode
                        )
                      }`
                    )
                }
              >
                Profil
              </button>

              <button
                className="primaryButton"
                onClick={
                  () =>
                    sendRequest(
                      result.friendCode
                    )
                }
              >
                Hinzufügen
              </button>
            </div>
          </div>
        ))}
      </section>

      {incoming.length > 0 && (
        <section className="friendSection">
          <h2>Anfragen</h2>

          {incoming.map((request) => (
            <div
              className="friendRow"
              key={request.id}
            >
              <div>
                <strong>
                  {request.user.displayName ??
                    "Cardyssey Collector"}
                </strong>

                <span>
                  {request.user.friendCode}
                </span>
              </div>

              <div className="friendActions">
                <button
                  className="ghostButton"
                  onClick={
                    () =>
                      removeRequest(
                        request.id
                      )
                  }
                >
                  Ablehnen
                </button>

                <button
                  className="primaryButton"
                  onClick={
                    () =>
                      accept(
                        request.id
                      )
                  }
                >
                  Annehmen
                </button>
              </div>
            </div>
          ))}
        </section>
      )}

      {outgoing.length > 0 && (
        <section className="friendSection">
          <h2>Gesendete Anfragen</h2>

          {outgoing.map((request) => (
            <div
              className="friendRow"
              key={request.id}
            >
              <div>
                <strong>
                  {request.user.displayName ??
                    "Cardyssey Collector"}
                </strong>

                <span>
                  {request.user.friendCode}
                </span>
              </div>

              <button
                className="ghostButton"
                onClick={
                  () =>
                    removeRequest(
                      request.id
                    )
                }
              >
                Zurückziehen
              </button>
            </div>
          ))}
        </section>
      )}

      <section className="friendSection">
        <h2>Meine Freunde</h2>

        {friends.length === 0 ? (
          <p className="muted">
            Noch keine Freunde hinzugefügt.
          </p>
        ) : (
          friends.map((friend) => (
            <div
              className="friendRow"
              key={friend.friendCode}
            >
              <div>
                <strong>
                  {friend.displayName ??
                    "Cardyssey Collector"}
                </strong>

                <span>
                  {friend.friendCode}
                </span>
              </div>

              <div className="friendActions">
                <button
                  className="ghostButton"
                  onClick={
                    () =>
                      router.push(
                        `/friends/${
                          encodeURIComponent(
                            friend.friendCode
                          )
                        }`
                      )
                  }
                >
                  Profil ansehen
                </button>

                <button
                  className="primaryButton"
                  onClick={
                    () =>
                      router.push(
                        `/chat?friend=${
                          encodeURIComponent(
                            friend.friendCode
                          )
                        }`
                      )
                  }
                >
                  Nachricht
                </button>
              </div>
            </div>
          ))
        )}
      </section>
    </>);
  return embedded?content:<AppShell active="/friends" user={user}>{content}</AppShell>;
}
