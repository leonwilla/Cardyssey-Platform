"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

type SearchResult = {
  id: string;
  localId: string;
  name: string;
  setId: string;
  setName?: string | null;
  imageBase?: string | null;
};

type CatalogVariant = {
  id: string;
  type: string;
  subtype?: string | null;
  foil?: string | null;
  size?: string | null;
  stamps: string[];
  legacyVariant: string;
  tcgDexEur?: number | null;
};

type CardDetails = {
  id: string;
  localId: string;
  name: string;
  languageCode: string;
  imageBase?: string | null;
  imageLanguage?: string | null;
  setId: string;
  setName: string;
  officialCount: number;
  rarity?: string | null;
  variants: CatalogVariant[];
};

const LANGUAGES = [
  ["de", "Deutsch"],
  ["en", "Englisch"],
  ["fr", "Französisch"],
  ["it", "Italienisch"],
  ["es", "Spanisch"],
  ["pt", "Portugiesisch"],
  ["ja", "Japanisch"],
  ["ko", "Koreanisch"],
  ["zh-tw", "Chinesisch (Trad.)"],
  ["zh-cn", "Chinesisch (Vereinf.)"],
] as const;

const CONDITIONS = [
  ["MINT", "Mint"],
  ["NEAR_MINT", "Near Mint"],
  ["EXCELLENT", "Excellent"],
  ["GOOD", "Good"],
  ["PLAYED", "Played"],
] as const;

function imageUrl(
  imageBase?: string | null
) {
  if (!imageBase) {
    return null;
  }

  return `${
    imageBase.replace(/\/$/, "")
  }/high.webp`;
}

function variantLabel(
  variant: CatalogVariant
) {
  return [
    variant.type,
    variant.subtype,
    variant.foil,
    ...variant.stamps,
  ]
    .filter(Boolean)
    .join(" · ");
}

function eur(
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

type Props = {
  open: boolean;
  busy?: boolean;
  initialCardId?: string | null;
  initialLanguage?: string;
  onClose: () => void;
  onAdded: () => Promise<void>;
};

export function AddCardDialog({
  open,
  busy = false,
  initialCardId = null,
  initialLanguage = "de",
  onClose,
  onAdded,
}: Props) {

  const [query, setQuery] =
    useState("");

  const [number, setNumber] =
    useState("");

  const [language, setLanguage] =
    useState("de");

  const [results, setResults] =
    useState<SearchResult[]>([]);

  const [selected, setSelected] =
    useState<CardDetails | null>(
      null
    );

  const [selectedVariantId, setSelectedVariantId] =
    useState("");

  const [condition, setCondition] =
    useState("NEAR_MINT");

  const [quantity, setQuantity] =
    useState(1);

  const [searching, setSearching] =
    useState(false);

  const [loadingDetails, setLoadingDetails] =
    useState(false);

  const [saving, setSaving] =
    useState(false);

  const [
    wishlistSaving,
    setWishlistSaving
  ] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    setSelected(null);
    setSelectedVariantId("");
  }, [language, open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const cleanQuery =
      query.trim();

    const cleanNumber =
      number.trim();

    if (
      cleanQuery.length < 2 &&
      cleanNumber.length === 0
    ) {
      setResults([]);
      setSearching(false);
      return;
    }

    const controller =
      new AbortController();

    const timer =
      window.setTimeout(
        async () => {
          setSearching(true);
          setError(null);

          try {
            const params =
              new URLSearchParams();

            if (cleanQuery) {
              params.set(
                "q",
                cleanQuery
              );
            }

            if (cleanNumber) {
              params.set(
                "number",
                cleanNumber
              );
            }

            params.set(
              "language",
              language
            );

            params.set(
              "limit",
              "20"
            );

            const response =
              await fetch(
                `/api/cards/search?${params.toString()}`,
                {
                  cache: "no-store",
                  signal:
                    controller.signal,
                }
              );

            if (
              response.status === 401
            ) {
              throw new Error(
                "Deine Sitzung ist abgelaufen."
              );
            }

            if (!response.ok) {
              throw new Error(
                "Kartensuche fehlgeschlagen."
              );
            }

            const data =
              (
                await response.json()
              ) as SearchResult[];

            setResults(data);

          } catch (e) {
            if (
              e instanceof DOMException &&
              e.name === "AbortError"
            ) {
              return;
            }

            setError(
              e instanceof Error
                ? e.message
                : "Kartensuche fehlgeschlagen."
            );

          } finally {
            setSearching(false);
          }
        },
        350
      );

    return () => {
      window.clearTimeout(
        timer
      );

      controller.abort();
    };

  }, [
    query,
    number,
    language,
    open,
  ]);

  async function selectCard(
    card: SearchResult
  ) {
    setLoadingDetails(true);
    setError(null);

    try {
      const response =
        await fetch(
          `/api/cards/${
            encodeURIComponent(
              card.id
            )
          }?language=${
            encodeURIComponent(
              language
            )
          }`,
          {
            cache: "no-store",
          }
        );

      if (!response.ok) {
        throw new Error(
          "Kartendetails konnten nicht geladen werden."
        );
      }

      const details =
        (
          await response.json()
        ) as CardDetails;

      setSelected(details);

      setSelectedVariantId(
        details.variants[0]?.id ??
          ""
      );

      setCondition(
        "NEAR_MINT"
      );

      setQuantity(1);

    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Kartendetails konnten nicht geladen werden."
      );

    } finally {
      setLoadingDetails(false);
    }
  }

  useEffect(() => {
    if (
      !open ||
      !initialCardId
    ) {
      return;
    }

    let cancelled = false;

    async function loadInitialCard() {
      setLoadingDetails(true);
      setError(null);

      try {
        const response =
          await fetch(
            `/api/cards/${
              encodeURIComponent(
                initialCardId!
              )
            }?language=${
              encodeURIComponent(
                initialLanguage
              )
            }`,
            {
              cache: "no-store",
            }
          );

        if (!response.ok) {
          throw new Error(
            "Kartendetails konnten nicht geladen werden."
          );
        }

        const details =
          (
            await response.json()
          ) as CardDetails;

        if (cancelled) {
          return;
        }

        setLanguage(
          initialLanguage
        );

        setSelected(
          details
        );

        setSelectedVariantId(
          details.variants[0]?.id ??
            ""
        );

        setCondition(
          "NEAR_MINT"
        );

        setQuantity(1);

      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? e.message
              : "Kartendetails konnten nicht geladen werden."
          );
        }

      } finally {
        if (!cancelled) {
          setLoadingDetails(false);
        }
      }
    }

    loadInitialCard();

    return () => {
      cancelled = true;
    };
  }, [
    open,
    initialCardId,
    initialLanguage,
  ]);

  const selectedVariant =
    useMemo(
      () =>
        selected?.variants.find(
          (variant) =>
            variant.id ===
            selectedVariantId
        ) ?? null,
      [
        selected,
        selectedVariantId,
      ]
    );

  async function addCard() {
    if (
      !selected ||
      !selectedVariant
    ) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const priceParams =
        new URLSearchParams({
          language:
            selected.languageCode,
          variantId:
            selectedVariant.id,
          condition,
        });

      let centralBaseEur:
        number | null = null;

      const priceResponse =
        await fetch(
          `/api/pricing/cards/${encodeURIComponent(selected.id)}?${priceParams.toString()}`,
          {
            cache: "no-store",
          }
        );

      if (priceResponse.ok) {
        const quote =
          await priceResponse.json() as {
            baseEur?: number | null;
            exactLanguageMatch?: boolean;
            exactVariantMatch?: boolean;
          };

        if (
          quote.exactLanguageMatch === true &&
          quote.exactVariantMatch === true &&
          typeof quote.baseEur === "number" &&
          Number.isFinite(quote.baseEur) &&
          quote.baseEur > 0
        ) {
          centralBaseEur =
            quote.baseEur;
        }
      }

      const marketUnitEur:
        Record<string, number> =
          centralBaseEur == null
            ? {}
            : { TCG: centralBaseEur };

      const item = {
        key:
          `web-${crypto.randomUUID()}`,

        cardId:
          selected.id,

        languageCode:
          selected.languageCode,

        name:
          selected.name,

        setId:
          selected.setId,

        setName:
          selected.setName,

        localId:
          selected.localId,

        imageBase:
          selected.imageBase ??
          null,

        imageLanguage:
          selected.imageLanguage ??
          null,

        variant:
          selectedVariant.legacyVariant,

        variantSpec: {
          id:
            selectedVariant.id,

          type:
            selectedVariant.type,

          subtype:
            selectedVariant.subtype ??
            null,

          foil:
            selectedVariant.foil ??
            null,

          size:
            selectedVariant.size ??
            null,

          stamps:
            selectedVariant.stamps,
        },

        condition,
        quantity,

        unitEur:
          centralBaseEur,

        unitUsd:
          null,

        marketUnitEur,

        marketUpdatedAtMs: {},
        marketSampleCount: {},
      };

      const response =
        await fetch(
          "/api/collection",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(item),
          }
        );

      if (!response.ok) {
        const body =
          await response
            .json()
            .catch(
              () => null
            );

        throw new Error(
          body?.error ===
            "invalid_collection_item"
            ? "Die Karte konnte nicht als gültiger Sammlungseintrag gespeichert werden."
            : "Karte konnte nicht gespeichert werden."
        );
      }

      await onAdded();

      setQuery("");
      setNumber("");
      setResults([]);
      setSelected(null);
      setSelectedVariantId("");
      setQuantity(1);
      setCondition(
        "NEAR_MINT"
      );

      onClose();

    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Speichern fehlgeschlagen."
      );

    } finally {
      setSaving(false);
    }
  }

  async function addToWishlist() {
    if (
      !selected ||
      !selectedVariant
    ) {
      return;
    }

    setWishlistSaving(true);
    setError(null);

    try {
      const response =
        await fetch(
          "/api/wishlist",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              cardId:
                selected.id,

              languageCode:
                selected.languageCode,

              name:
                selected.name,

              setId:
                selected.setId,

              setName:
                selected.setName,

              localId:
                selected.localId,

              imageBase:
                selected.imageBase ??
                null,

              variantId:
                selectedVariant.id,

              variantType:
                selectedVariant.type,

              variantSubtype:
                selectedVariant.subtype ??
                null,

              foil:
                selectedVariant.foil ??
                null,

              size:
                selectedVariant.size ??
                null,

              stamps:
                selectedVariant.stamps,

            }),
          }
        );

      if (!response.ok) {
        const body =
          await response
            .json()
            .catch(() => null);

        if (
          response.status === 409 ||
          body?.error ===
            "already_on_wishlist"
        ) {
          throw new Error(
            "Diese Kartenvariante steht bereits auf deiner Wishlist."
          );
        }

        throw new Error(
          "Karte konnte nicht zur Wishlist hinzugefügt werden."
        );
      }

      setError(
        "✓ Zur Wishlist hinzugefügt."
      );

    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Wishlist konnte nicht gespeichert werden."
      );

    } finally {
      setWishlistSaving(false);
    }
  }

  if (!open) {
    return null;
  }

  const disabled =
    busy ||
    saving ||
    wishlistSaving;

  const selectedImage =
    imageUrl(
      selected?.imageBase
    );

  return (
    <div
      className="modalBackdrop"
      onMouseDown={
        disabled
          ? undefined
          : onClose
      }
    >
      <div
        className="addCardModal"
        onMouseDown={
          (event) =>
            event.stopPropagation()
        }
      >
        <div className="editorHeader">
          <div>
            <span className="eyebrowText">
              Sammlung
            </span>

            <h2>
              Karte hinzufügen
            </h2>

            <p>
              Suche echte Kartendaten
              im Cardyssey-Katalog.
            </p>
          </div>

          <button
            type="button"
            className="iconButton"
            onClick={onClose}
            disabled={disabled}
            aria-label="Schließen"
          >
            ×
          </button>
        </div>

        {!selected ? (
          <>
            <div className="addCardSearchFields">
              <label className="editorField">
                <span>
                  Kartenname
                </span>

                <input
                  type="search"
                  value={query}
                  onChange={
                    (event) =>
                      setQuery(
                        event.target.value
                      )
                  }
                  placeholder="z. B. Pikachu"
                  autoFocus
                />
              </label>

              <label className="editorField">
                <span>
                  Kartennummer
                </span>

                <input
                  value={number}
                  onChange={
                    (event) =>
                      setNumber(
                        event.target.value
                      )
                  }
                  placeholder="z. B. 025/165"
                />
              </label>

              <label className="editorField">
                <span>
                  Sprache
                </span>

                <select
                  value={language}
                  onChange={
                    (event) =>
                      setLanguage(
                        event.target.value
                      )
                  }
                >
                  {LANGUAGES.map(
                    (
                      [
                        value,
                        label,
                      ]
                    ) => (
                      <option
                        key={value}
                        value={value}
                      >
                        {label}
                      </option>
                    )
                  )}
                </select>
              </label>
            </div>

            {error && (
              <div className="addCardError">
                {error}
              </div>
            )}

            <div className="addCardResultsHeader">
              <strong>
                Treffer
              </strong>

              <span>
                {searching
                  ? "Suche …"
                  : `${results.length} gefunden`}
              </span>
            </div>

            <div className="addCardResults">
              {!searching &&
                results.length ===
                  0 && (
                  <div className="addCardEmpty">
                    Gib einen Kartennamen
                    oder eine Kartennummer
                    ein.
                  </div>
                )}

              {results.map(
                (card) => {
                  const image =
                    imageUrl(
                      card.imageBase
                    );

                  return (
                    <button
                      type="button"
                      className="addCardResult"
                      key={card.id}
                      onClick={
                        () =>
                          selectCard(
                            card
                          )
                      }
                      disabled={
                        loadingDetails
                      }
                    >
                      <div className="addCardResultImage">
                        {image ? (
                          <img
                            src={image}
                            alt=""
                          />
                        ) : (
                          <div className="miniCardPlaceholder">
                            CARD
                          </div>
                        )}
                      </div>

                      <div>
                        <strong>
                          {card.name}
                        </strong>

                        <span>
                          {card.setName ??
                            "Set wird nach Auswahl geladen"}
                        </span>

                        <small>
                          #{card.localId}
                          {" · "}
                          {card.id}
                        </small>
                      </div>

                      <span className="addCardChevron">
                        ›
                      </span>
                    </button>
                  );
                }
              )}
            </div>
          </>
        ) : (
          <>
            <button
              type="button"
              className="addCardBack"
              onClick={
                () => {
                  setSelected(
                    null
                  );
                  setSelectedVariantId(
                    ""
                  );
                }
              }
              disabled={disabled}
            >
              ← Zurück zur Suche
            </button>

            <div className="addCardSelected">
              <div className="addCardSelectedImage">
                {selectedImage ? (
                  <img
                    src={selectedImage}
                    alt={selected.name}
                  />
                ) : (
                  <div className="cardImagePlaceholder" />
                )}
              </div>

              <div className="addCardSelectedInfo">
                <span className="eyebrowText">
                  {selected.rarity ??
                    "Karte"}
                </span>

                <h3>
                  {selected.name}
                </h3>

                <p>
                  {selected.setName}
                  {" · #"}
                  {selected.localId}
                </p>

                <div className="chips">
                  <span className="chip">
                    {selected.languageCode.toUpperCase()}
                  </span>

                  <span className="chip mutedChip">
                    {selected.officialCount}
                    {" Karten im Set"}
                  </span>
                </div>
              </div>
            </div>

            {error && (
              <div className="addCardError">
                {error}
              </div>
            )}

            <label className="editorField">
              <span>
                Physische Variante
              </span>

              {selected.variants.length >
              0 ? (
                <select
                  value={
                    selectedVariantId
                  }
                  onChange={
                    (event) =>
                      setSelectedVariantId(
                        event.target.value
                      )
                  }
                  disabled={disabled}
                >
                  {selected.variants.map(
                    (variant) => (
                      <option
                        key={variant.id}
                        value={variant.id}
                      >
                        {variantLabel(
                          variant
                        )}
                      </option>
                    )
                  )}
                </select>
              ) : (
                <div className="addCardError">
                  Für diese Karte wurden
                  keine Varianten gefunden.
                </div>
              )}
            </label>

            {selectedVariant && (
              <div className="variantIdentityPanel">
                <div>
                  <span>
                    Varianten-ID
                  </span>
                  <strong>
                    {selectedVariant.id}
                  </strong>
                </div>

                <div>
                  <span>
                    Marktpreis
                  </span>
                  <strong>
                    {eur(
                      selectedVariant.tcgDexEur
                    )}
                  </strong>
                </div>
              </div>
            )}

            <div className="addCardFormGrid">
              <label className="editorField">
                <span>
                  Zustand
                </span>

                <select
                  value={condition}
                  onChange={
                    (event) =>
                      setCondition(
                        event.target.value
                      )
                  }
                  disabled={disabled}
                >
                  {CONDITIONS.map(
                    (
                      [
                        value,
                        label,
                      ]
                    ) => (
                      <option
                        key={value}
                        value={value}
                      >
                        {label}
                      </option>
                    )
                  )}
                </select>
              </label>

              <div className="editorField">
                <span>
                  Menge
                </span>

                <div className="quantityControl">
                  <button
                    type="button"
                    onClick={
                      () =>
                        setQuantity(
                          Math.max(
                            1,
                            quantity - 1
                          )
                        )
                    }
                    disabled={
                      disabled ||
                      quantity <= 1
                    }
                  >
                    −
                  </button>

                  <strong>
                    {quantity}
                  </strong>

                  <button
                    type="button"
                    onClick={
                      () =>
                        setQuantity(
                          quantity + 1
                        )
                    }
                    disabled={disabled}
                  >
                    +
                  </button>
                </div>
              </div>
            </div>

            <div className="editorActions">
              <button
                type="button"
                className="ghostButton"
                onClick={onClose}
                disabled={disabled}
              >
                Abbrechen
              </button>

              <button
              type="button"
              className="ghostButton wishlistButton"
              onClick={addToWishlist}
              disabled={
                disabled ||
                !selectedVariant
              }
            >
              {wishlistSaving
                ? "Speichert …"
                : "♡ Zur Wishlist"}
            </button>

            <button
                type="button"
                className="primaryButton"
                onClick={addCard}
                disabled={
                  disabled ||
                  !selectedVariant
                }
              >
                {saving
                  ? "Wird hinzugefügt …"
                  : "Zur Sammlung hinzufügen"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
