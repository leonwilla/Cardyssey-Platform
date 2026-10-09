"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";

const scanLanguages = [
  {
    api: "de",
    label: "Deutsch",
    ocr: "deu",
  },
  {
    api: "en",
    label: "Englisch",
    ocr: "eng",
  },
  {
    api: "ja",
    label: "Japanisch",
    ocr: "jpn",
  },
  {
    api: "ko",
    label: "Koreanisch",
    ocr: "kor",
  },
  {
    api: "zh-tw",
    label: "Chinesisch (trad.)",
    ocr: "chi_tra",
  },
  {
    api: "zh-cn",
    label: "Chinesisch (vereinf.)",
    ocr: "chi_sim",
  },
] as const;

type ScanLanguage =
  (typeof scanLanguages)[number];

function scanLanguageLabel(
  code: string | undefined
) {
  return (
    scanLanguages.find(
      (language) =>
        language.api === code
    )?.label ??
    code?.toUpperCase() ??
    "Unbekannt"
  );
}

export default function ScanPage() {
  const router = useRouter();

  const videoRef =
    useRef<HTMLVideoElement | null>(null);

  const streamRef =
    useRef<MediaStream | null>(null);

  const [cameraActive, setCameraActive] =
    useState(false);

  const [image, setImage] =
    useState<string | null>(null);

  const [error, setError] =
    useState<string | null>(null);

  const [recognizing, setRecognizing] =
    useState(false);

  const [ocrText, setOcrText] =
    useState("");

  const [candidates, setCandidates] =
    useState<any[]>([]);

  const [languageCode, setLanguageCode] =
    useState<ScanLanguage["api"]>("de");

  const [automaticLanguage, setAutomaticLanguage] =
    useState(true);

  const selectedLanguage = useMemo(
    () =>
      scanLanguages.find(
        (language) =>
          language.api === languageCode
      ) ?? scanLanguages[0],
    [languageCode]
  );

  async function startCamera() {
    setError(null);
    setImage(null);
    setCandidates([]);
    setOcrText("");

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: {
              ideal: "environment",
            },
          },
          audio: false,
        });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      setCameraActive(true);
    } catch {
      setError(
        "Kamera konnte nicht geöffnet werden."
      );
    }
  }

  function stopCamera() {
    streamRef.current
      ?.getTracks()
      .forEach(
        (track) => track.stop()
      );

    streamRef.current = null;
    setCameraActive(false);
  }

  function capture() {
    const video =
      videoRef.current;

    if (!video) return;

    const canvas =
      document.createElement("canvas");

    canvas.width =
      video.videoWidth;

    canvas.height =
      video.videoHeight;

    const context =
      canvas.getContext("2d");

    if (!context) return;

    context.drawImage(
      video,
      0,
      0,
      canvas.width,
      canvas.height
    );

    setImage(
      canvas.toDataURL(
        "image/jpeg",
        0.92
      )
    );

    stopCamera();
  }

  function selectImage(
    event:
      React.ChangeEvent<HTMLInputElement>
  ) {
    const file =
      event.target.files?.[0];

    if (!file) return;

    stopCamera();
    setError(null);
    setCandidates([]);
    setOcrText("");

    const reader =
      new FileReader();

    reader.onload = () => {
      if (
        typeof reader.result ===
        "string"
      ) {
        setImage(reader.result);
      }
    };

    reader.readAsDataURL(file);
  }

  async function recognizeCard() {
    if (!image) return;

    setRecognizing(true);
    setError(null);
    setCandidates([]);

    try {
      const {
        createWorker,
      } = await import("tesseract.js");

      const ocrLanguages =
        automaticLanguage
          ? scanLanguages.map(
              (language) =>
                language.ocr
            )
          : selectedLanguage.ocr;

      const worker =
        await createWorker(
          ocrLanguages
        );

      const result =
        await worker.recognize(image);

      await worker.terminate();

      const text =
        result.data.text.trim();

      setOcrText(text);

      /*
       * Numberless promos and special cards can have little or no OCR-readable
       * text. The backend also supports perceptual image matching, so keep
       * going with an empty OCR string instead of rejecting the scan.
       */
      const languagesToSearch =
        automaticLanguage
          ? scanLanguages
          : [selectedLanguage];

      const recognized =
        await Promise.all(
          languagesToSearch.map(
            async (language) => {
              const response =
                await fetch(
                  "/api/cards/recognize",
                  {
                    method: "POST",
                    headers: {
                      "Content-Type":
                        "application/json",
                    },
                    body: JSON.stringify({
                      text,
                      language:
                        language.api,
                      imageBase64:
                        image,
                    }),
                  }
                );

              if (!response.ok) {
                return [];
              }

              const data =
                await response.json();

              return (
                data.candidates ?? []
              ).map(
                (card: any) => ({
                  ...card,
                  recognizedLanguage:
                    language.api,
                })
              );
            }
          )
        );

      const unique =
        new Map<string, any>();

      recognized
        .flat()
        .forEach((card) => {
          if (!unique.has(card.id)) {
            unique.set(
              card.id,
              card
            );
          }
        });

      const nextCandidates =
        [...unique.values()];

      if (
        nextCandidates.length === 0
      ) {
        throw new Error(
          "Karte konnte nicht eindeutig zugeordnet werden."
        );
      }

      setCandidates(
        nextCandidates
      );
    } catch (recognitionError) {
      setError(
        recognitionError instanceof Error
          ? recognitionError.message
          : "Erkennung fehlgeschlagen."
      );
    } finally {
      setRecognizing(false);
    }
  }

  useEffect(() => {
    return () => {
      streamRef.current
        ?.getTracks()
        .forEach(
          (track) => track.stop()
        );
    };
  }, []);

  return (
    <AppShell active="/scan">
      <section className="pageIntro scannerPageIntro">
        <div>
          <span className="eyebrowText">
            Scannen
          </span>

          <h1>Kartenscanner</h1>

          <p>
            Karte groß ausrichten,
            aufnehmen und direkt
            deiner Sammlung zuordnen.
          </p>
        </div>

        <label className="scannerLanguageControl">
          <span>Sprache</span>

          <select
            value={languageCode}
            disabled={automaticLanguage}
            onChange={(event) =>
              setLanguageCode(
                event.target.value as
                  ScanLanguage["api"]
              )
            }
          >
            {scanLanguages.map(
              (language) => (
                <option
                  key={language.api}
                  value={language.api}
                >
                  {language.label}
                </option>
              )
            )}
          </select>
        </label>
      </section>

      <section className="scannerWorkspace">
        <div className="scannerFrame webScannerFrame">
          {cameraActive ? (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="scannerMedia"
            />
          ) : image ? (
            <img
              src={image}
              alt="Aufgenommene Karte"
              className="scannerMedia contain"
            />
          ) : (
            <div className="scannerEmpty">
              <span>KAMERA</span>
              <strong>
                Bereit für deine Karte
              </strong>
              <small>
                Starte die Kamera oder
                wähle ein Bild aus.
              </small>
            </div>
          )}

          <div
            className="scannerCardGuide"
            aria-hidden="true"
          >
            <span className="scanLine" />
          </div>

        </div>

        <div className="scannerModeBlock">
          <div className="scannerModeLabel">
            <span>SCAN-MODUS</span>
            <small>
              {automaticLanguage
                ? "Sprache automatisch"
                : "Sprache manuell"}
            </small>
          </div>

          <div className="scannerModeSwitch">
            <button
              type="button"
              className={
                !automaticLanguage
                  ? "selected"
                  : ""
              }
              onClick={() =>
                setAutomaticLanguage(false)
              }
            >
              STANDARD
            </button>

            <button
              type="button"
              className={
                automaticLanguage
                  ? "selected"
                  : ""
              }
              onClick={() =>
                setAutomaticLanguage(true)
              }
            >
              AUTO
            </button>
          </div>
        </div>

        {error && (
          <div className="statusPanel errorPanel scannerError">
            {error}
          </div>
        )}

        <div className="scannerActions">
          {!cameraActive && (
            <button
              className="primaryButton scannerMainAction"
              onClick={startCamera}
            >
              Kamera starten
            </button>
          )}

          {cameraActive && (
            <button
              className="primaryButton scannerMainAction"
              onClick={capture}
            >
              Foto aufnehmen
            </button>
          )}

          <label className="ghostButton scannerGalleryAction">
            Bild auswählen

            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={selectImage}
              hidden
            />
          </label>
        </div>

        {image && (
          <div className="scannerReviewActions">
            <button
              className="ghostButton"
              onClick={() => {
                setImage(null);
                setCandidates([]);
                setOcrText("");
              }}
            >
              Neu aufnehmen
            </button>

            <button
              className="primaryButton"
              onClick={recognizeCard}
              disabled={recognizing}
            >
              {recognizing
                ? "Erkenne Karte …"
                : "Karte erkennen"}
            </button>
          </div>
        )}

        {candidates.length > 0 && (
          <div className="scannerCandidates scannerResultPanel">
            <span className="eyebrowText">
              Erkannte Karten
            </span>

            <div className="scannerCandidateGrid">
              {candidates.map(
                (card) => (
                  <button
                    type="button"
                    className="scannerCandidate"
                    key={card.id}
                    onClick={() =>
                      router.push(
                        `/collection?addCard=${encodeURIComponent(
                          card.id
                        )}&language=${encodeURIComponent(
                          card.recognizedLanguage ??
                            selectedLanguage.api
                        )}`
                      )
                    }
                  >
                    <strong>
                      {card.name}
                    </strong>

                    <span>
                      {card.setName ??
                        card.setId}
                      {" · #"}
                      {card.localId}
                      {" · "}
                      {scanLanguageLabel(
                        card.recognizedLanguage ??
                          selectedLanguage.api
                      )}
                    </span>

                    <small>
                      Zur Sammlung hinzufügen →
                    </small>
                  </button>
                )
              )}
            </div>
          </div>
        )}

        {ocrText && (
          <details className="scannerOcrDebug">
            <summary>
              Erkannten Text anzeigen
            </summary>

            <pre>{ocrText}</pre>
          </details>
        )}
      </section>
    </AppShell>
  );
}
