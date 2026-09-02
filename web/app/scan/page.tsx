"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";

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

  async function startCamera() {
    setError(null);
    setImage(null);

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

    const reader =
      new FileReader();

    reader.onload = () => {
      if (
        typeof reader.result ===
        "string"
      ) {
        setImage(
          reader.result
        );
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

      const worker =
        await createWorker("deu");

      const result =
        await worker.recognize(image);

      await worker.terminate();

      const text =
        result.data.text.trim();

      setOcrText(text);

      if (!text) {
        throw new Error(
          "Auf dem Bild konnte kein Text erkannt werden."
        );
      }

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
              language: "de",
            }),
          }
        );

      if (!response.ok) {
        throw new Error(
          "Karte konnte nicht zugeordnet werden."
        );
      }

      const data =
        await response.json();

      setCandidates(
        data.candidates ?? []
      );

    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
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
      <section className="pageIntro">
        <div>
          <span className="eyebrowText">
            Scanner
          </span>

          <h1>
            Karte erkennen
          </h1>

          <p>
            Karte fotografieren oder
            ein vorhandenes Bild auswählen.
          </p>
        </div>

        {candidates.length > 0 && (
          <div className="scannerCandidates">
            <span className="eyebrowText">
              Erkannte Karten
            </span>

            {candidates.map(
              (card) => (
                <button
                  type="button"
                  className="scannerCandidate"
                  key={card.id}
                  onClick={
                    () =>
                      router.push(
                        `/collection?addCard=${
                          encodeURIComponent(
                            card.id
                          )
                        }&language=de`
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
                  </span>
                </button>
              )
            )}
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

      <section className="scannerPanel">

        <div className="scannerFrame">

          {cameraActive ? (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
          ) : image ? (
            <img
              src={image}
              alt="Aufgenommene Karte"
              style={{
                width: "100%",
                height: "100%",
                objectFit: "contain",
              }}
            />
          ) : (
            <>
              <span className="scanLine" />
              <div className="scanCorners" />
            </>
          )}

        </div>

        {error && (
          <div className="statusPanel errorPanel">
            {error}
          </div>
        )}

        <div className="scannerActions">

          {!cameraActive && (
            <button
              className="primaryButton"
              onClick={startCamera}
            >
              Kamera starten
            </button>
          )}

          {cameraActive && (
            <button
              className="primaryButton"
              onClick={capture}
            >
              Foto aufnehmen
            </button>
          )}

          <label className="ghostButton">
            Bild auswählen

            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={selectImage}
              hidden
            />
          </label>

          {image && (
            <button
              className="ghostButton"
              onClick={
                () => setImage(null)
              }
            >
              Neu aufnehmen
            </button>
          )}


          {image && (
            <button
              className="primaryButton"
              onClick={recognizeCard}
              disabled={recognizing}
            >
              {recognizing
                ? "Erkenne Karte …"
                : "Karte erkennen"}
            </button>
          )}

        </div>
      </section>
    </AppShell>
  );
}
