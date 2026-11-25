"use client";

import "../deck.css";
import "../marketplace/market.css";

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

export default function OffersPage({embedded=false,onDiscover,onCounts}:{embedded?:boolean;onDiscover?:()=>void;onCounts?:(c:{incoming:number;outgoing:number;pending:number})=>void}={}) {
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

  useEffect(() => {
    onCounts?.({
      incoming: incoming.length,
      outgoing: outgoing.length,
      pending: incoming.filter((o) => o.status === "PENDING").length,
    });
  }, [incoming, outgoing, onCounts]);

  const items =
    tab === "incoming"
      ? incoming
      : outgoing;

  const content = (
    <section className={embedded ? "mk-offers" : "dk mk-offers"}>
      {!embedded && (
        <section className="dk-deck">
          <span className="dk-eyebrow">Marktplatz</span>
          <h1 className="dk-title">Angebote</h1>
          <p className="dk-sub">Kaufangebote senden, prüfen und verwalten.</p>
        </section>
      )}
      <div className="mk-offersHead">
        <div>
          <h2>Kaufangebote</h2>
          <p>Anfragen zu deinen Karten und Angebote, die du verschickt hast.</p>
        </div>
        <div className="dk-seg" role="tablist" aria-label="Kaufangebote filtern">
          <button type="button" role="tab" aria-selected={tab === "incoming"} className={tab === "incoming" ? "on" : ""} onClick={() => setTab("incoming")}>
            Eingehend<b>{incoming.length}</b>
          </button>
          <button type="button" role="tab" aria-selected={tab === "outgoing"} className={tab === "outgoing" ? "on" : ""} onClick={() => setTab("outgoing")}>
            Gesendet<b>{outgoing.length}</b>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="dk-empty">Angebote werden geladen …</div>
      ) : items.length === 0 ? (
        <div className="mk-emptyDeal" role="status">
          <div className="mk-emptySlots" aria-hidden="true"><i /><i /><i /></div>
          <div>
            <h3>{tab === "incoming" ? "Noch keine eingehenden Angebote" : "Noch keine gesendeten Angebote"}</h3>
            <p>{tab === "incoming"
              ? "Wenn jemand eine deiner Karten kaufen möchte, liegt die Anfrage hier wie ein Deal-Ticket bereit."
              : "Du hast noch kein Kaufangebot verschickt. Stöbere bei anderen Sammlern und mach ein Angebot."}</p>
            {embedded && onDiscover && (
              <button type="button" className="dk-ghost" onClick={onDiscover}>Karten entdecken →</button>
            )}
          </div>
        </div>
      ) : (
        <div className="mk-deals">
          {items.map((offer) => {
            const image = imageUrl(offer.imageBase);
            const pending = offer.status === "PENDING";
            const diff =
              offer.offerPriceEur != null && offer.listingPriceEur
                ? Math.round((offer.offerPriceEur / offer.listingPriceEur - 1) * 100)
                : null;
            const person = tab === "incoming"
              ? offer.buyerDisplayName ?? offer.buyerFriendCode
              : offer.sellerDisplayName ?? offer.sellerFriendCode;
            return (
              <article className={"mk-deal " + offer.status.toLowerCase()} key={offer.id}>
                <div className="mk-dealArt">
                  {image ? <img src={image} alt={offer.name} loading="lazy" /> : null}
                </div>
                <div className="mk-dealBody">
                  <div className="mk-dealTop">
                    <div>
                      <span className="mk-dealSet">{offer.setName ?? "Trading Card"}</span>
                      <h3>{offer.name}</h3>
                      <small>#{offer.localId ?? "—"} · {offer.variant} · {offer.condition} · {offer.quantity}×</small>
                    </div>
                    <span className={"mk-status " + offer.status.toLowerCase()}>{statusLabel(offer.status)}</span>
                  </div>
                  <div className="mk-dealPrices">
                    <div className="mk-offerPrice"><small>Angebot</small><strong>{money(offer.offerPriceEur)}</strong></div>
                    <div><small>Listenpreis</small><strong>{money(offer.listingPriceEur)}</strong></div>
                    {diff != null && <span className={"mk-diff" + (diff < 0 ? " down" : "")}>{diff > 0 ? "+" : ""}{diff} %</span>}
                  </div>
                  {offer.message && <p className="mk-dealMsg">{offer.message}</p>}
                  <div className="mk-dealFoot">
                    <span className="mk-person"><i>{String(person).charAt(0).toUpperCase()}</i>{tab === "incoming" ? "Von " : "An "}<b>{person}</b></span>
                    {pending && tab === "incoming" && (
                      <span className="mk-dealActions">
                        <button type="button" className="dk-ghost" disabled={busyId === offer.id} onClick={() => action(offer.id, "reject")}>Ablehnen</button>
                        <button type="button" className="dk-gold" disabled={busyId === offer.id} onClick={() => action(offer.id, "accept")}>Annehmen</button>
                      </span>
                    )}
                    {pending && tab === "outgoing" && (
                      <button type="button" className="dk-ghost" disabled={busyId === offer.id} onClick={() => action(offer.id, "withdraw")}>Zurückziehen</button>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
  return embedded?content:<AppShell active="/offers" user={user}>{content}</AppShell>;
}
