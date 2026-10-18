"use client";

import Image from "next/image";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import type {
  MarketplaceOfferResponse,
} from "@/lib/generated/cardyssey/src";

import type {
  User,
} from "@/lib/types";

import {
  AppShell,
} from "@/components/AppShell";

type Tab =
  | "incoming"
  | "outgoing";

function money(
  value?: number | null
) {
  return value == null
    ? "—"
    : new Intl.NumberFormat(
        "de-DE",
        {
          style: "currency",
          currency: "EUR",
        }
      ).format(value);
}

function imageUrl(
  base?: string | null
) {
  return base
    ? `${
        base.replace(
          /\/$/,
          ""
        )
      }/high.webp`
    : null;
}

function statusLabel(
  value: string
) {
  switch (value) {
    case "PENDING":
      return "Offen";

    case "ACCEPTED":
      return "Angenommen";

    case "REJECTED":
      return "Abgelehnt";

    case "WITHDRAWN":
      return "Zurückgezogen";

    default:
      return value;
  }
}

export default function OffersPage() {
  const router =
    useRouter();

  const [user, setUser] =
    useState<User | null>(
      null
    );

  const [tab, setTab] =
    useState<Tab>(
      "incoming"
    );

  const [incoming, setIncoming] =
    useState<
      MarketplaceOfferResponse[]
    >([]);

  const [outgoing, setOutgoing] =
    useState<
      MarketplaceOfferResponse[]
    >([]);

  const [loading, setLoading] =
    useState(true);

  const [busyId, setBusyId] =
    useState<string | null>(
      null
    );

  const load =
    useCallback(
      async () => {
        setLoading(true);

        const [
          me,
          incomingResponse,
          outgoingResponse,
        ] =
          await Promise.all([
            fetch(
              "/api/auth/me",
              {
                cache:
                  "no-store",
              }
            ),

            fetch(
              "/api/offers/incoming",
              {
                cache:
                  "no-store",
              }
            ),

            fetch(
              "/api/offers/outgoing",
              {
                cache:
                  "no-store",
              }
            ),
          ]);

        if (
          me.status === 401
        ) {
          router.replace(
            "/login"
          );

          return;
        }

        if (me.ok) {
          setUser(
            await me.json()
          );
        }

        setIncoming(
          incomingResponse.ok
            ? await incomingResponse.json()
            : []
        );

        setOutgoing(
          outgoingResponse.ok
            ? await outgoingResponse.json()
            : []
        );

        setLoading(false);
      },
      [
        router,
      ]
    );

  useEffect(
    () => {
      void load();
    },
    [
      load,
    ]
  );

  async function action(
    id: string,
    action:
      | "accept"
      | "reject"
      | "withdraw"
  ) {
    setBusyId(id);

    const response =
      action === "withdraw"
        ? await fetch(
            `/api/offers/${
              encodeURIComponent(
                id
              )
            }`,
            {
              method:
                "DELETE",
            }
          )
        : await fetch(
            `/api/offers/${
              encodeURIComponent(
                id
              )
            }/${action}`,
            {
              method:
                "POST",
            }
          );

    setBusyId(null);

    if (response.ok) {
      await load();
    }
  }

  const items =
    tab === "incoming"
      ? incoming
      : outgoing;

  return (
    <AppShell
      active="/offers"
      user={user}
    >
      <div className="pageIntro">
        <div>
          <span className="eyebrowText">
            Marketplace
          </span>

          <h1>Angebote</h1>

          <p>
            Kaufangebote senden,
            prüfen und verwalten.
          </p>
        </div>
      </div>

      <div className="offerTabs">
        <button
          className={
            tab === "incoming"
              ? "active"
              : ""
          }
          onClick={
            () =>
              setTab(
                "incoming"
              )
          }
        >
          Eingehend
          <span>
            {incoming.length}
          </span>
        </button>

        <button
          className={
            tab === "outgoing"
              ? "active"
              : ""
          }
          onClick={
            () =>
              setTab(
                "outgoing"
              )
          }
        >
          Gesendet
          <span>
            {outgoing.length}
          </span>
        </button>
      </div>

      {loading ? (
        <div className="statusPanel">
          Angebote werden
          geladen …
        </div>
      ) : items.length === 0 ? (
        <div className="statusPanel">
          {tab === "incoming"
            ? "Du hast aktuell keine eingehenden Angebote."
            : "Du hast aktuell keine gesendeten Angebote."}
        </div>
      ) : (
        <div className="offerGrid">
          {items.map(
            (offer) => {
              const image =
                imageUrl(
                  offer.imageBase
                );

              const pending =
                offer.status ===
                "PENDING";

              return (
                <article
                  className="offerCard"
                  key={offer.id}
                >
                  <div className="offerImage">
                    {image ? (
                      <Image width={280} height={390} unoptimized
                        src={image}
                        alt={
                          offer.name
                        }
                      />
                    ) : (
                      <div className="cardImagePlaceholder" />
                    )}
                  </div>

                  <div className="offerContent">
                    <div className="offerTop">
                      <div>
                        <span className="eyebrowText">
                          {offer.setName ??
                            "Trading Card"}
                        </span>

                        <h3>
                          {
                            offer.name
                          }
                        </h3>

                        <small className="muted">
                          #
                          {offer.localId ??
                            "—"}
                          {" · "}
                          {
                            offer.variant
                          }
                          {" · "}
                          {
                            offer.condition
                          }
                        </small>
                      </div>

                      <span
                        className={
                          `offerStatus ${
                            offer.status.toLowerCase()
                          }`
                        }
                      >
                        {statusLabel(
                          offer.status
                        )}
                      </span>
                    </div>

                    <div className="offerPrices">
                      <div>
                        <small>
                          Angebot
                        </small>

                        <strong>
                          {money(
                            offer.offerPriceEur
                          )}
                        </strong>
                      </div>

                      <div>
                        <small>
                          Listenpreis
                        </small>

                        <strong>
                          {money(
                            offer.listingPriceEur
                          )}
                        </strong>
                      </div>

                      <div>
                        <small>
                          Menge
                        </small>

                        <strong>
                          {
                            offer.quantity
                          }×
                        </strong>
                      </div>
                    </div>

                    {offer.message && (
                      <p className="offerMessage">
                        “
                        {
                          offer.message
                        }
                        ”
                      </p>
                    )}

                    <div className="offerPerson">
                      {tab ===
                      "incoming"
                        ? (
                          <>
                            Von{" "}
                            <b>
                              {offer.buyerDisplayName ??
                                offer.buyerFriendCode}
                            </b>
                          </>
                        )
                        : (
                          <>
                            An{" "}
                            <b>
                              {offer.sellerDisplayName ??
                                offer.sellerFriendCode}
                            </b>
                          </>
                        )}
                    </div>

                    {pending &&
                      tab ===
                        "incoming" && (
                        <div className="offerActions">
                          <button
                            className="primaryButton"
                            disabled={
                              busyId ===
                              offer.id
                            }
                            onClick={
                              () =>
                                action(
                                  offer.id,
                                  "accept"
                                )
                            }
                          >
                            Annehmen
                          </button>

                          <button
                            className="ghostButton"
                            disabled={
                              busyId ===
                              offer.id
                            }
                            onClick={
                              () =>
                                action(
                                  offer.id,
                                  "reject"
                                )
                            }
                          >
                            Ablehnen
                          </button>
                        </div>
                      )}

                    {pending &&
                      tab ===
                        "outgoing" && (
                        <button
                          className="ghostButton offerWithdraw"
                          disabled={
                            busyId ===
                            offer.id
                          }
                          onClick={
                            () =>
                              action(
                                offer.id,
                                "withdraw"
                              )
                          }
                        >
                          Angebot zurückziehen
                        </button>
                      )}
                  </div>
                </article>
              );
            }
          )}
        </div>
      )}
    </AppShell>
  );
}
