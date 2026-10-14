/** Card IDs are shared between languages; language is part of recognition identity. */
export function mergeScanCandidates<T extends { id: string; recognizedLanguage?: string }>(
  groups: T[][]
): T[] {
  const unique = new Map<string, T>();
  for (const card of groups.flat()) {
    const key = `${card.recognizedLanguage ?? ""}:${card.id}`;
    if (!unique.has(key)) unique.set(key, card);
  }
  return [...unique.values()];
}

/** Also bounds work such as OCR startup which does not accept an AbortSignal. */
export function withAbort<T>(work: Promise<T>, signal: AbortSignal): Promise<T> {
  return new Promise((resolve, reject) => {
    const abort = () => reject(new DOMException("Aborted", "AbortError"));
    if (signal.aborted) {
      // Still consume rejection of already-started work.
      void work.catch(() => {});
      abort();
      return;
    }
    signal.addEventListener("abort", abort, { once: true });
    work.then(resolve, reject).finally(() => signal.removeEventListener("abort", abort));
  });
}
