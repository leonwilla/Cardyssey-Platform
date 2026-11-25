"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import "../deck.css";
import "./scan.css";
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
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

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
                (card: any) => ({
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
        (result): result is PromiseFulfilledResult<any[]> => result.status === "fulfilled"
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

  /** Photo, screenshot or drag & drop: scale to max 1600 px, same path as the camera. */
  async function takeImageFile(file: File | null | undefined) {
    if (!file || !file.type.startsWith("image/")) {
      if (file) setError("Bitte ein Bild (JPG, PNG, WEBP) wählen.");
      return;
    }
    stopCamera();
    setError(null);
    setCandidates([]);
    setOcrText("");
    try {
      const url = URL.createObjectURL(file);
      const img = new Image();
      await new Promise<void>((resolve, reject) => { img.onload = () => resolve(); img.onerror = () => reject(new Error()); img.src = url; });
      const scale = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.naturalWidth * scale);
      canvas.height = Math.round(img.naturalHeight * scale);
      canvas.getContext("2d")?.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      setImage(canvas.toDataURL("image/jpeg", 0.92));
    } catch {
      setError("Das Bild konnte nicht gelesen werden.");
    }
  }

  useEffect(() => {
    function onPaste(event: ClipboardEvent) {
      const file = [...(event.clipboardData?.items ?? [])].find((item) => item.type.startsWith("image/"))?.getAsFile();
      if (file) { event.preventDefault(); void takeImageFile(file); }
    }
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  });

  const resetScan = () => { setImage(null); setCandidates([]); setOcrText(""); setError(null); };
  const stage = candidates.length ? 3 : image ? 2 : 1;

  return (
    <AppShell active="/scan">
      <div className="dk scanPage">
        <section className="dk-deck" aria-label="Kartenscanner">
          <div className="dk-deckGrid">
            <div>
              <span className="dk-eyebrow">Scannen</span>
              <h1 className="dk-title">Kartenscanner</h1>
              <p className="dk-sub">Foto oder Screenshot rein, Karte erkennen, in die Sammlung legen. Klappt auch mit Bildern aus eBay- oder Cardmarket-Anzeigen.</p>
              <div className="scanSteps" aria-label="Ablauf">
                {["Bild", "Erkennen", "Hinzufügen"].map((label, index) => (
                  <span key={label} className={stage > index + 1 ? "done" : stage === index + 1 ? "on" : ""}><b>{index + 1}</b>{label}</span>
                ))}
              </div>
            </div>
            <div className="scanLang">
              <span className="dk-eyebrow">Sprache der Karte</span>
              <div className="dk-toggle" role="group" aria-label="Spracherkennung">
                <button type="button" className={automaticLanguage ? "on" : ""} onClick={() => setAutomaticLanguage(true)}>Automatisch</button>
                <button type="button" className={!automaticLanguage ? "on" : ""} onClick={() => setAutomaticLanguage(false)}>Festlegen</button>
              </div>
              {!automaticLanguage && (
                <label className="dk-deckSelect">Sprache
                  <select value={languageCode} onChange={(event) => setLanguageCode(event.target.value as ScanLanguage["api"])}>
                    {scanLanguages.map((language) => <option key={language.api} value={language.api}>{language.label}</option>)}
                  </select>
                </label>
              )}
              <small>{automaticLanguage ? "Sucht in allen 6 Sprachen – etwas langsamer." : `Sucht nur auf ${selectedLanguage.label} – schneller.`}</small>
            </div>
          </div>
        </section>

        <section className="scanWork">
          <div
            className={"scanStage" + (dragging ? " drag" : "") + (image || cameraActive ? " filled" : "")}
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); void takeImageFile(event.dataTransfer.files?.[0]); }}
          >
            {cameraActive ? (
              <video ref={videoRef} autoPlay playsInline muted className="scanMedia" />
            ) : image ? (
              <img src={image} alt="Gewählte Karte" className="scanMedia contain" />
            ) : (
              <div className="scanDrop">
                <div className="scanGhostCard" aria-hidden="true"><span>?</span></div>
                <strong className="onDesk">Karte hier ablegen</strong>
                <strong className="onTouch">Bereit für deine Karte</strong>
                <small className="onDesk">Bild hierher ziehen, <kbd>Strg</kbd>+<kbd>V</kbd> zum Einfügen oder rechts auswählen</small>
                <small className="onTouch">Tippe auf „Foto oder Screenshot wählen“ – die Kamera öffnet sich direkt.</small>
              </div>
            )}
            <div className="scanCorners" aria-hidden="true"><i /><i /><i /><i />{(cameraActive || recognizing) && <span className="scanBeam" />}</div>
          </div>

          <aside className="scanSide">
            {!image && !cameraActive && (
              <>
                <button type="button" className="scanSource primary" onClick={() => fileInput.current?.click()} disabled={recognizing}>
                  <span className="scanIcon">🖼</span><span><b>Foto oder Screenshot wählen</b><small>Am Handy öffnet sich direkt die Kamera</small></span>
                </button>
                <input ref={fileInput} type="file" accept="image/*" capture="environment" hidden onChange={(event) => { void takeImageFile(event.target.files?.[0]); event.target.value = ""; }} />
                <button type="button" className="scanSource" onClick={startCamera} disabled={cameraStarting || recognizing}>
                  <span className="scanIcon">📷</span><span><b>{cameraStarting ? "Kamera wird geöffnet …" : "Live-Kamera"}</b><small>Webcam oder Handy-Kamera im Browser</small></span>
                </button>
                <div className="scanSource tip">
                  <span className="scanIcon">📋</span><span><b>Bild einfügen</b><small>Screenshot kopieren, dann hier <kbd>Strg</kbd>+<kbd>V</kbd></small></span>
                </div>
              </>
            )}
            {cameraActive && (
              <>
                <button type="button" className="dk-gold scanBig" onClick={capture}>● Foto aufnehmen</button>
                <button type="button" className="dk-ghost" onClick={stopCamera}>Kamera schließen</button>
                <p className="scanHint">Karte gerade und formatfüllend in den Rahmen halten, ohne Spiegelung.</p>
              </>
            )}
            {image && (
              <>
                <button type="button" className="dk-gold scanBig" onClick={recognizeCard} disabled={recognizing}>{recognizing ? "Erkenne Karte …" : "✦ Karte erkennen"}</button>
                <button type="button" className="dk-ghost" disabled={recognizing} onClick={resetScan}>Anderes Bild</button>
                {recognizing && <p className="scanHint">Text und Bild werden abgeglichen{automaticLanguage ? " – in allen Sprachen" : ""}. Das dauert ein paar Sekunden.</p>}
              </>
            )}
            {error && <div className="statusPanel errorPanel" role="alert">{error}</div>}
          </aside>
        </section>

        {candidates.length > 0 && (
          <section aria-label="Erkannte Karten" style={{ display: "grid", gap: 12 }}>
            <div className="scanResultHead"><h2>Treffer</h2><span className="dk-count">{candidates.length} mögliche Karten · antippen zum Hinzufügen</span></div>
            <div className="dk-binder">
              {candidates.map((card, index) => {
                const language = card.recognizedLanguage ?? selectedLanguage.api;
                const img = card.imageBase ? `${String(card.imageBase).replace(/\/$/, "")}/low.webp` : null;
                return (
                  <button type="button" className="dk-pocket" key={card.recognizedLanguage + ":" + card.id}
                    onClick={() => router.push(`/collection?addCard=${encodeURIComponent(card.id)}&language=${encodeURIComponent(language)}`)}>
                    <div className="dk-art">
                      {img && <img src={img} alt={card.name} loading="lazy" />}
                      {index === 0 && <span className="dk-badge gold">Bester Treffer</span>}
                      <span className="dk-plus">+ Zur Sammlung</span>
                    </div>
                    <div className="dk-name">{card.name}</div>
                    <div className="dk-meta">{card.setName ?? card.setId} · #{card.localId} · {scanLanguageLabel(language)}</div>
                  </button>
                );
              })}
            </div>
          </section>
        )}

        {ocrText && (
          <details className="scannerOcrDebug">
            <summary>Erkannten Text anzeigen</summary>
            <pre>{ocrText}</pre>
          </details>
        )}
      </div>
    </AppShell>
  );
}
