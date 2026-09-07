"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  useParams,
  useRouter,
} from "next/navigation";

import {
  AppShell,
} from "@/components/AppShell";

import {
  FriendWishlistSection,
} from "@/components/FriendWishlistSection";

import type {
  User,
} from "@/lib/types";

type FriendSetProgress = {
  setId: string;
  setName?: string | null;
  ownedCards: number;
  totalCards?: number | null;
};

type SharedCollectionCard = {
  cardId: string;
  name: string;
  setId?: string | null;
  setName?: string | null;
  localId?: string | null;
  imageBase?: string | null;
  variant: string;
  quantity?: number | null;
};

type SharedCollection = {
  totalValueEur?: number | null;
  cards: SharedCollectionCard[];
};

type ShowcaseItem = {
  collectionItemId: string;
  position: number;
  cardId: string;
  name: string;
  setName?: string | null;
  localId?: string | null;
  imageBase?: string | null;
  variant: string;
};

type Profile = {
  friendCode: string;
  displayName?: string | null;
  avatarUrl?: string | null;
  isFriend: boolean;
  canSeeShowcase: boolean;
  canSeeCollection: boolean;
  canSeeCollectionValue: boolean;
  canSeeQuantity: boolean;
  canSeeSets: boolean;
  canSeeWishlist: boolean;
};

export default function FriendProfilePage() {
  const params =
    useParams<{
      friendCode: string;
    }>();

  const router =
    useRouter();

  const [user, setUser] =
    useState<User | null>(null);

  const [profile, setProfile] =
    useState<Profile | null>(null);

  const [showcase, setShowcase] =
    useState<ShowcaseItem[]>([]);

  const [
    sharedCollection,
    setSharedCollection
  ] =
    useState<SharedCollection | null>(
      null
    );

  const [
    friendSets,
    setFriendSets
  ] =
    useState<FriendSetProgress[]>([]);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const code =
        decodeURIComponent(
          params.friendCode
        );

      const [me, profileResponse] =
        await Promise.all([
          fetch("/api/auth/me"),
          fetch(
            `/api/friends/${
              encodeURIComponent(code)
            }`,
            { cache: "no-store" }
          ),
        ]);

      if (me.status === 401) {
        router.replace("/login");
        return;
      }

      if (me.ok) {
        setUser(await me.json());
      }

      if (
        profileResponse.status === 403
      ) {
        setError(
          "Dieses Profil ist privat."
        );
        return;
      }

      if (!profileResponse.ok) {
        setError(
          "Profil konnte nicht geladen werden."
        );
        return;
      }

      const loadedProfile =
        (await profileResponse.json()) as Profile;

      setProfile(
        loadedProfile
      );

      if (loadedProfile.canSeeSets) {
        const setsResponse =
          await fetch(
            `/api/friends/${
              encodeURIComponent(code)
            }/sets`,
            {
              cache: "no-store",
            }
          );

        if (setsResponse.ok) {
          setFriendSets(
            await setsResponse.json()
          );
        }
      }

      if (loadedProfile.canSeeCollection) {
        const collectionResponse =
          await fetch(
            `/api/friends/${
              encodeURIComponent(code)
            }/collection`,
            {
              cache: "no-store",
            }
          );

        if (collectionResponse.ok) {
          setSharedCollection(
            await collectionResponse.json()
          );
        }
      }

      if (loadedProfile.canSeeShowcase) {
        const showcaseResponse =
          await fetch(
            `/api/friends/${
              encodeURIComponent(code)
            }/showcase`,
            { cache: "no-store" }
          );

        if (showcaseResponse.ok) {
          setShowcase(
            await showcaseResponse.json()
          );
        }
      }
    }

    load();
  }, [
    params.friendCode,
    router,
  ]);

  async function removeFriend() {
    if (!profile) return;

    if (
      !window.confirm(
        `${profile.displayName ?? "Diesen Nutzer"} wirklich als Freund entfernen?`
      )
    ) {
      return;
    }

    const response =
      await fetch(
        `/api/friends/${
          encodeURIComponent(
            profile.friendCode
          )
        }`,
        { method: "DELETE" }
      );

    if (response.ok) {
      router.push("/friends");
    }
  }

  return (
    <AppShell
      active="/friends"
      user={user}
    >
      {error ? (
        <div className="statusPanel errorPanel">
          {error}
        </div>
      ) : profile ? (
        <>
          <section className="friendProfileHero">
            <div className="avatar large">
              {profile.avatarUrl ? (
                <img
                  src={profile.avatarUrl}
                  alt="Profilbild"
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    borderRadius: "inherit",
                    display: "block",
                  }}
                />
              ) : (
                (profile.displayName ||
                  "C")
                  .charAt(0)
                  .toUpperCase()
              )}
            </div>

            <div>
              <span className="eyebrowText">
                Sammlerprofil
              </span>

              <h1>
                {profile.displayName ??
                  "Cardyssey Collector"}
              </h1>

              <p>
                {profile.friendCode}
              </p>
            </div>

            {profile.isFriend && (
              <button
                className="ghostButton"
                onClick={removeFriend}
              >
                Freund entfernen
              </button>
            )}
          </section>

          {profile.canSeeShowcase && (
            <section className="friendShowcase">
              <span className="eyebrowText">
                Showcase
              </span>

              <h2>
                Lieblingskarten
              </h2>

              {showcase.length === 0 ? (
                <p className="muted">
                  Noch keine Karten im Showcase.
                </p>
              ) : (
                <div className="friendShowcaseGrid">
                  {showcase.map((item) => {
                    const image =
                      item.imageBase
                        ? `${item.imageBase.replace(/\/$/, "")}/high.webp`
                        : null;

                    return (
                      <article
                        key={item.collectionItemId}
                        className="friendShowcaseCard"
                      >
                        <span>
                          #{item.position}
                        </span>

                        {image ? (
                          <img
                            src={image}
                            alt={item.name}
                          />
                        ) : (
                          <div className="cardImagePlaceholder" />
                        )}

                        <strong>
                          {item.name}
                        </strong>

                        <small>
                          {item.setName ??
                            "Unbekanntes Set"}
                        </small>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          )}

          {profile.canSeeCollection &&
            sharedCollection && (
              <section className="friendCollectionSection">
                <div className="sectionTitle">
                  <div>
                    <span className="eyebrowText">
                      Sammlung
                    </span>

                    <h2>
                      Karten
                    </h2>
                  </div>

                  {sharedCollection.totalValueEur != null && (
                    <strong className="friendCollectionValue">
                      {new Intl.NumberFormat(
                        "de-DE",
                        {
                          style: "currency",
                          currency: "EUR",
                        }
                      ).format(
                        sharedCollection.totalValueEur
                      )}
                    </strong>
                  )}
                </div>

                <div className="cardGrid">
                  {sharedCollection.cards.map(
                    (card, index) => {

                      const image =
                        card.imageBase
                          ? `${card.imageBase.replace(/\/$/, "")}/high.webp`
                          : null;

                      return (
                        <article
                          className="cardTile"
                          key={`${card.cardId}-${index}`}
                        >
                          <div className="cardImageWrap">
                            {image ? (
                              <img
                                className="cardImage"
                                src={image}
                                alt={card.name}
                              />
                            ) : (
                              <div className="cardImagePlaceholder" />
                            )}

                            {card.quantity != null && (
                              <span className="qtyBadge">
                                {card.quantity}×
                              </span>
                            )}
                          </div>

                          <div className="cardMeta">
                            <strong>
                              {card.name}
                            </strong>

                            <div className="muted">
                              #{card.localId ?? "—"}
                              {" · "}
                              {card.setName ??
                                "Unbekanntes Set"}
                            </div>

                            <div className="chips">
                              <span className="chip">
                                {card.variant}
                              </span>
                            </div>
                          </div>
                        </article>
                      );
                    }
                  )}
                </div>
              </section>
            )}

          {profile.canSeeSets && (
            <section className="friendSetsSection">
              <span className="eyebrowText">
                Sets
              </span>

              <h2>
                Set-Fortschritt
              </h2>

              {friendSets.length === 0 ? (
                <p className="muted">
                  Noch keine Sets begonnen.
                </p>
              ) : (
                <div className="friendSetsGrid">
                  {friendSets.map((set) => {

                    const percentage =
                      set.totalCards &&
                      set.totalCards > 0
                        ? Math.min(
                            100,
                            Math.round(
                              (
                                set.ownedCards /
                                set.totalCards
                              ) * 100
                            )
                          )
                        : null;

                    return (
                      <article
                        className="friendSetCard"
                        key={set.setId}
                      >
                        <div>
                          <strong>
                            {set.setName ??
                              set.setId}
                          </strong>

                          <small>
                            {set.totalCards != null
                              ? `${set.ownedCards} / ${set.totalCards} Karten`
                              : `${set.ownedCards} Karten gesammelt`}
                          </small>
                        </div>

                        {percentage != null && (
                          <>
                            <div className="friendSetProgress">
                              <span
                                style={{
                                  width:
                                    `${percentage}%`,
                                }}
                              />
                            </div>

                            <b>
                              {percentage}%
                            </b>
                          </>
                        )}
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          )}

          <FriendWishlistSection
            friendCode={profile.friendCode}
            visible={profile.canSeeWishlist}
          />

          <section className="profileVisibilityGrid">
            <div className="statCard">
              <span>Showcase</span>
              <strong>
                {profile.canSeeShowcase
                  ? "Sichtbar"
                  : "Privat"}
              </strong>
            </div>

            <div className="statCard">
              <span>Sammlung</span>
              <strong>
                {profile.canSeeCollection
                  ? "Sichtbar"
                  : "Privat"}
              </strong>
            </div>

            <div className="statCard">
              <span>Set-Fortschritt</span>
              <strong>
                {profile.canSeeSets
                  ? "Sichtbar"
                  : "Privat"}
              </strong>
            </div>

            <div className="statCard">
              <span>Wishlist</span>
              <strong>
                {profile.canSeeWishlist
                  ? "Sichtbar"
                  : "Privat"}
              </strong>
            </div>
          </section>
        </>
      ) : (
        <div className="statusPanel">
          Profil wird geladen …
        </div>
      )}
    </AppShell>
  );
}
