"use client";

import Image from "next/image";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { mergeScanCandidates, withAbort } from "@/lib/scan-candidates";

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

type ScanCandidate = {
  id: string;
  name: string;
  setName?: string | null;
  setId?: string | null;
  localId?: string | null;
  recognizedLanguage?: string;
};

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

  const cameraGeneration = useRef(0);
  const recognitionController = useRef<AbortController | null>(null);
  const ocrWorker = useRef<import("tesseract.js").Worker | null>(null);
  const [cameraStarting, setCameraStarting] = useState(false);

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
    useState<ScanCandidate[]>([]);

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
    if (cameraStarting) return;
    stopCamera();
    const generation = ++cameraGeneration.current;
    setCameraStarting(true);
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

      if (generation !== cameraGeneration.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;

      setCameraActive(true);
    } catch {
      if (generation === cameraGeneration.current) {
        setError("Kamera konnte nicht geöffnet werden. Bitte Kameraberechtigung prüfen.");
      }
    } finally {
      if (generation === cameraGeneration.current) setCameraStarting(false);
    }
  }

  function stopCamera() {
    cameraGeneration.current += 1;
    setCameraStarting(false);
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

    if (!video || video.readyState < 2 || !video.videoWidth || !video.videoHeight) {
      setError("Die Kamera lädt noch. Bitte kurz warten und erneut aufnehmen.");
      return;
    }

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

  async function recognizeCard() {
    if (!image || recognitionController.current) return;
    const controller = new AbortController();
    recognitionController.current = controller;
    const timeout = window.setTimeout(() => {
      controller.abort();
      void ocrWorker.current?.terminate().catch(() => {});
    }, 90_000);
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

      let text = "";
      let worker: import("tesseract.js").Worker | null = null;
      try {
        worker = await withAbort(createWorker(ocrLanguages, 1, {
          workerPath: "/vendor/tesseract/worker.min.js",
          corePath: "/vendor/tesseract",
        }).then((created) => {
          if (controller.signal.aborted) {
            void created.terminate().catch(() => {});
            throw new DOMException("Aborted", "AbortError");
          }
          ocrWorker.current = created;
          return created;
        }), controller.signal);
        if (controller.signal.aborted) throw new DOMException("Aborted", "AbortError");
        if (!worker) throw new Error("OCR konnte nicht gestartet werden.");
        const result = await withAbort(worker.recognize(image), controller.signal);
        text = result.data.text.trim();
      } catch (ocrError) {
        // Image recognition remains usable when OCR language downloads fail.
        if (controller.signal.aborted) throw ocrError;
      } finally {
        if (worker) await worker.terminate().catch(() => {});
        if (ocrWorker.current === worker) ocrWorker.current = null;
      }
      if (controller.signal.aborted) throw new DOMException("Aborted", "AbortError");

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
        await Promise.allSettled(
          languagesToSearch.map(
            async (language) => {
              const response =
                await fetch(
                  "/api/cards/recognize",
                  {
                    method: "POST",
                    signal: controller.signal,
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
                throw new Error(response.status === 401
                  ? "Bitte melde dich erneut an."
                  : "Kartenerkennung ist vorübergehend nicht erreichbar.");
              }

              const data =
                await response.json();

              return (
                data.candidates ?? []
              ).map(
                (card: ScanCandidate) => ({
                  ...card,
                  recognizedLanguage:
                    language.api,
                })
              );
            }
          )
        );

      if (controller.signal.aborted) throw new DOMException("Aborted", "AbortError");
      const successful = recognized.filter(
        (result): result is PromiseFulfilledResult<ScanCandidate[]> => result.status === "fulfilled"
      );
      if (successful.length === 0) {
        const failed = recognized.find((result) => result.status === "rejected");
        throw failed?.status === "rejected" ? failed.reason : new Error("Erkennung fehlgeschlagen.");
      }
      const nextCandidates = mergeScanCandidates(successful.map((result) => result.value));

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
        controller.signal.aborted
          ? "Erkennung abgebrochen oder Zeitlimit erreicht. Bitte erneut versuchen."
          : recognitionError instanceof Error
          ? recognitionError.message
          : "Erkennung fehlgeschlagen."
      );
    } finally {
      window.clearTimeout(timeout);
      if (recognitionController.current === controller) recognitionController.current = null;
      setRecognizing(false);
    }
  }

  useEffect(() => {
    if (!cameraActive || !videoRef.current || !streamRef.current) return;
    const video = videoRef.current;
    video.srcObject = streamRef.current;
    void video.play().catch(() => setError("Kameravorschau konnte nicht starten. Bitte Kamera erneut öffnen."));
    return () => { video.srcObject = null; };
  }, [cameraActive]);

  useEffect(() => {
    return () => {
      cameraGeneration.current += 1;
      recognitionController.current?.abort();
      void ocrWorker.current?.terminate().catch(() => {});
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
            <Image width={480} height={672} unoptimized
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
                Starte die Kamera und
                richte deine Karte aus.
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
              disabled={cameraStarting || recognizing}
            >
              {cameraStarting ? "Kamera wird geöffnet …" : "Kamera starten"}
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

        </div>

        {image && (
          <div className="scannerReviewActions">
            <button
              className="ghostButton"
              disabled={recognizing}
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
                    key={card.recognizedLanguage + ":" + card.id}
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
