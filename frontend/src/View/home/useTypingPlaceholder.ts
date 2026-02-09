import { useEffect, useState } from "react";

const PHRASES = [
  "이 기술, 기존 특허랑 겹치나요?",
  "이 아이디어로 특허 낼 수 있을까요?",
  "이 특허, 실제로 쓸 수 있는 시장이 있나요?",
];

const TYPING_INTERVAL_MS = 80;
const DELETING_INTERVAL_MS = 40;
const PAUSE_AT_END_MS = 2000;
const PAUSE_AT_START_MS = 500;

/**
 * Returns a string that animates through phrases with a typewriter effect.
 */
export function useTypingPlaceholder(): string {
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [visibleLength, setVisibleLength] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);

  const phrase = PHRASES[phraseIndex] ?? PHRASES[0];

  useEffect(() => {
    if (isDeleting) {
      if (visibleLength <= 0) {
        setIsDeleting(false);
        setPhraseIndex((i) => (i + 1) % PHRASES.length);
        const t = setTimeout(() => setVisibleLength(1), PAUSE_AT_START_MS);
        return () => clearTimeout(t);
      }
      const t = setTimeout(
        () => setVisibleLength((n) => n - 1),
        DELETING_INTERVAL_MS
      );
      return () => clearTimeout(t);
    }

    if (visibleLength >= phrase.length) {
      const t = setTimeout(() => setIsDeleting(true), PAUSE_AT_END_MS);
      return () => clearTimeout(t);
    }

    const t = setTimeout(
      () => setVisibleLength((n) => n + 1),
      TYPING_INTERVAL_MS
    );
    return () => clearTimeout(t);
  }, [phrase, visibleLength, isDeleting]);

  return phrase.slice(0, visibleLength);
}
