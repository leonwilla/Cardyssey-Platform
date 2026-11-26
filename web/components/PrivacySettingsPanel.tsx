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
  ["showcaseVisibility", "Vitrine"],
  ["collectionVisibility", "Sammlung"],
  ["collectionValueVisibility", "Sammlungswert"],
  ["quantityVisibility", "Kartenmengen"],
  ["setsVisibility", "Set-Fortschritt"],
  ["wishlistVisibility", "Wunschliste"],
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

              <div className="privacyChoice" role="radiogroup" aria-label={title}>
                {(["PUBLIC", "FRIENDS", "PRIVATE"] as Visibility[]).map((value) => (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={settings[key] === value}
                    className={(settings[key] === value ? "on " : "") + value.toLowerCase()}
                    onClick={() => changeVisibility(key, value)}
                  >
                    {labels[value]}
                  </button>
                ))}
              </div>
            </div>
          )
        )}

        <div className="privacyRow">
          <strong>
            Vitrinen-Größe
          </strong>

          <div className="privacyChoice" role="radiogroup" aria-label="Vitrinen-Größe">
            {([5, 10] as const).map((size) => (
              <button
                key={size}
                type="button"
                role="radio"
                aria-checked={settings.showcaseSize === size}
                className={settings.showcaseSize === size ? "on" : ""}
                onClick={() => setSettings({ ...settings, showcaseSize: size })}
              >
                Top {size}
              </button>
            ))}
          </div>
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
