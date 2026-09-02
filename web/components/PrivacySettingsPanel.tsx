"use client";

import {
  useEffect,
  useState,
} from "react";

type Visibility =
  | "PUBLIC"
  | "FRIENDS"
  | "PRIVATE";

type Settings = {
  profileVisibility: Visibility;
  showcaseVisibility: Visibility;
  collectionVisibility: Visibility;
  collectionValueVisibility: Visibility;
  quantityVisibility: Visibility;
  setsVisibility: Visibility;
  wishlistVisibility: Visibility;
  showcaseSize: 5 | 10;
};

const labels: Record<Visibility, string> = {
  PUBLIC: "Alle",
  FRIENDS: "Nur Freunde",
  PRIVATE: "Niemand",
};

const fields = [
  ["profileVisibility", "Profil"],
  ["showcaseVisibility", "Showcase"],
  ["collectionVisibility", "Sammlung"],
  ["collectionValueVisibility", "Sammlungswert"],
  ["quantityVisibility", "Kartenmengen"],
  ["setsVisibility", "Set-Fortschritt"],
  ["wishlistVisibility", "Wishlist"],
] as const;

export function PrivacySettingsPanel() {
  const [settings, setSettings] =
    useState<Settings | null>(null);

  const [saving, setSaving] =
    useState(false);

  const [message, setMessage] =
    useState<string | null>(null);

  useEffect(() => {
    fetch("/api/privacy", {
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error();
        }

        return response.json();
      })
      .then(setSettings)
      .catch(() =>
        setMessage(
          "Privatsphäre-Einstellungen konnten nicht geladen werden."
        )
      );
  }, []);

  function changeVisibility(
    key: keyof Settings,
    value: Visibility
  ) {
    if (!settings) return;

    setSettings({
      ...settings,
      [key]: value,
    });
  }

  async function save() {
    if (!settings) return;

    setSaving(true);
    setMessage(null);

    const response =
      await fetch("/api/privacy", {
        method: "PUT",
        headers: {
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify(settings),
      });

    setSaving(false);

    setMessage(
      response.ok
        ? "Privatsphäre gespeichert."
        : "Speichern fehlgeschlagen."
    );
  }

  if (!settings) {
    return (
      <div className="statusPanel">
        {message ??
          "Privatsphäre wird geladen …"}
      </div>
    );
  }

  return (
    <section className="privacyPanel">
      <div className="privacyHead">
        <div>
          <span className="eyebrowText">
            Privatsphäre
          </span>

          <h2>
            Wer darf was sehen?
          </h2>

          <p>
            Du entscheidest für jeden
            Bereich separat.
          </p>
        </div>
      </div>

      <div className="privacyRows">
        {fields.map(
          ([key, title]) => (
            <div
              className="privacyRow"
              key={key}
            >
              <strong>{title}</strong>

              <select
                value={
                  settings[key] as Visibility
                }
                onChange={
                  (event) =>
                    changeVisibility(
                      key,
                      event.target
                        .value as Visibility
                    )
                }
              >
                {(
                  [
                    "PUBLIC",
                    "FRIENDS",
                    "PRIVATE",
                  ] as Visibility[]
                ).map((value) => (
                  <option
                    key={value}
                    value={value}
                  >
                    {labels[value]}
                  </option>
                ))}
              </select>
            </div>
          )
        )}

        <div className="privacyRow">
          <strong>
            Showcase-Größe
          </strong>

          <select
            value={settings.showcaseSize}
            onChange={
              (event) =>
                setSettings({
                  ...settings,
                  showcaseSize:
                    Number(
                      event.target.value
                    ) as 5 | 10,
                })
            }
          >
            <option value={5}>
              Top 5
            </option>

            <option value={10}>
              Top 10
            </option>
          </select>
        </div>
      </div>

      {message && (
        <div className="statusPanel">
          {message}
        </div>
      )}

      <button
        className="primaryButton"
        onClick={save}
        disabled={saving}
      >
        {saving
          ? "Speichert …"
          : "Privatsphäre speichern"}
      </button>
    </section>
  );
}
