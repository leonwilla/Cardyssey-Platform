"use client";

import {
  useEffect,
  useState,
} from "react";

import { previewThemeKey } from "./PreviewThemeSync";

import {
  appearanceThemes,
  applyAppearanceTheme,
  cachedAppearanceTheme,
  isAppearanceTheme,
  type AppearanceTheme,
} from "./ThemeSync";

export function AppearanceSettingsPanel() {
  const [selected, setSelected] =
    useState<AppearanceTheme>(
      "OBSIDIAN_GOLD"
    );

  const [experimental, setExperimental] = useState(false);

  const [saving, setSaving] =
    useState(false);

  const [message, setMessage] =
    useState<string | null>(null);

  useEffect(() => {
    setExperimental(window.localStorage.getItem(previewThemeKey) === "1");
    setSelected(
      cachedAppearanceTheme()
    );

    fetch("/api/appearance", {
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error();
        }

        return response.json();
      })
      .then((settings) => {
        if (
          isAppearanceTheme(
            settings.theme
          )
        ) {
          setSelected(settings.theme);
          applyAppearanceTheme(
            settings.theme
          );
        }
      })
      .catch(() => {
        setMessage(
          "Server-Design konnte nicht geladen werden. Das zuletzt verwendete Design bleibt aktiv."
        );
      });
  }, []);

  async function selectTheme(
    theme: AppearanceTheme
  ) {
    const previous = selected;

    setSelected(theme);
    setSaving(true);
    setMessage(null);
    applyAppearanceTheme(theme);

    try {
      const response =
        await fetch(
          "/api/appearance",
          {
            method: "PUT",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              theme,
            }),
          }
        );

      if (!response.ok) {
        throw new Error();
      }

      setMessage(
        "Design gespeichert und mit Android synchronisiert."
      );
    } catch {
      setSelected(previous);
      applyAppearanceTheme(previous);
      setMessage(
        "Design konnte nicht auf dem Server gespeichert werden."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="appearancePanel">
      <span className="eyebrowText">
        Erscheinungsbild
      </span>

      <h2>Dein Cardyssey-Design</h2>

      <p className="muted">
        Die Auswahl wird in deinem Konto
        gespeichert und automatisch in
        Web und Android übernommen.
      </p>

      <div className="themeChoiceGrid">
        {appearanceThemes.map(
          (theme) => (
            <button
              type="button"
              key={theme.id}
              className={
                selected === theme.id
                  ? "themeChoice selected"
                  : "themeChoice"
              }
              disabled={saving}
              onClick={() =>
                selectTheme(theme.id)
              }
            >
              <span className="themeSwatches">
                {theme.colors.map(
                  (color) => (
                    <i
                      key={color}
                      style={{
                        background: color,
                      }}
                    />
                  )
                )}
              </span>

              <strong>{theme.name}</strong>
              <small>
                {theme.description}
              </small>

              <span className="themeSelectedLabel">
                {selected === theme.id
                  ? "Aktiv"
                  : "Auswählen"}
              </span>
            </button>
          )
        )}
      </div>

      <div className="statusPanel" style={{marginTop:20,display:"grid",gap:12}}>
        <strong>Neues helles Redesign (experimentell)</strong>
        <p>Nur in diesem Browser testen. Dein gespeichertes dunkles Cardyssey-Design und die Android-App bleiben unverändert.</p>
        <label style={{display:"flex",alignItems:"center",gap:10,cursor:"pointer"}}>
          <input type="checkbox" checked={experimental} onChange={event => {
            const next = event.target.checked;
            setExperimental(next);
            if (next) window.localStorage.setItem(previewThemeKey, "1");
            else window.localStorage.removeItem(previewThemeKey);
            window.dispatchEvent(new Event("cardyssey-redesign-change"));
          }} />
          Helles Testdesign in der Webapp verwenden
        </label>
        <small>Du kannst jederzeit wieder ausschalten. Diese Einstellung wird nicht mit Android synchronisiert.</small>
      </div>

      {message && (
        <div className="statusPanel">
          {message}
        </div>
      )}
    </section>
  );
}
