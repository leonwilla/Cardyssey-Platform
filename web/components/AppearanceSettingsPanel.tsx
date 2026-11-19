"use client";

import {
  useEffect,
  useState,
} from "react";

import {applyBrightness,cachedBrightness,type BrightnessMode} from "./ThemeSync";

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

  const [brightness,setBrightness]=useState<BrightnessMode>("light");

  const [saving, setSaving] =
    useState(false);

  const [message, setMessage] =
    useState<string | null>(null);

  useEffect(() => {
    setBrightness(cachedBrightness());
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
        Die Farbvariante wird mit deinem Cardyssey-Konto synchronisiert.
        Die Helligkeit kannst du aktuell für diesen Browser wählen.
      </p>

      <div className="brightnessChooser" aria-label="Helligkeit auswählen">
        <div><strong>Helligkeit</strong><small>Wähle die Helligkeit für das Cardyssey-Layout.</small></div>
        <div className="brightnessChoices" role="group" aria-label="Helligkeit">
          <button type="button" aria-pressed={brightness==="light"} onClick={()=>{setBrightness("light");applyBrightness("light")}}>☀ Hell</button>
          <button type="button" aria-pressed={brightness==="dark"} onClick={()=>{setBrightness("dark");applyBrightness("dark")}}>☾ Dunkel</button>
        </div>
      </div>

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

      {message && (
        <div className="statusPanel">
          {message}
        </div>
      )}
    </section>
  );
}
