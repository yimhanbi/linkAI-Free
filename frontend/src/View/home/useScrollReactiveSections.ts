import type { RefObject } from "react";
import { useEffect, useRef, useState } from "react";

/**
 * Observes scroll position and returns the index of the section
 * that is currently most in view (by intersection ratio).
 */
export function useScrollReactiveSections(
  containerRef: RefObject<HTMLDivElement | null>,
  sectionCount: number
): number {
  const [activeIndex, setActiveIndex] = useState(0);
  const ratiosRef = useRef<Map<Element, number>>(new Map());

  useEffect(() => {
    const container = containerRef.current;
    if (!container || sectionCount <= 0) return;

    const blocks = container.querySelectorAll<HTMLElement>("[data-scroll-section]");
    if (blocks.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          ratiosRef.current.set(entry.target, entry.intersectionRatio);
        });
        let bestIndex = 0;
        let bestRatio = 0;
        blocks.forEach((el, i) => {
          const ratio = ratiosRef.current.get(el) ?? 0;
          if (ratio > bestRatio) {
            bestRatio = ratio;
            bestIndex = i;
          }
        });
        setActiveIndex(bestIndex);
      },
      {
        root: null,
        rootMargin: "-20% 0px -60% 0px",
        threshold: [0, 0.25, 0.5, 0.75, 1],
      }
    );

    blocks.forEach((block) => observer.observe(block));
    return () => observer.disconnect();
  }, [containerRef, sectionCount]);

  return activeIndex;
}
