import type { RefObject } from "react";
import { useEffect, useState } from "react";

/**
 * Scroll-spy: 가장 화면 중앙에 가까운 섹션(visible 범위 내)을 active로 설정.
 */
export function useScrollReactiveSections(
  containerRef: RefObject<HTMLDivElement | null>,
  sectionCount: number
): number {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (sectionCount <= 0) return;

    const handleScroll = () => {
      const container = containerRef.current;
      if (!container) return;

      const blocks = container.querySelectorAll<HTMLElement>("[data-scroll-section]");
      if (!blocks.length) {
        setActiveIndex(0);
        return;
      }

      const viewportHeight =
        window.innerHeight || document.documentElement.clientHeight || 0;
      const viewportCenter = viewportHeight * 0.5;

      let bestIndex = 0;
      let bestDistance = Number.POSITIVE_INFINITY;

      blocks.forEach((el, index) => {
        const rect = el.getBoundingClientRect();
        // 화면 밖으로 완전히 나간 섹션은 제외
        if (rect.bottom <= 0 || rect.top >= viewportHeight) {
          return;
        }
        const sectionCenter = rect.top + rect.height * 0.4;
        const distance = Math.abs(sectionCenter - viewportCenter);
        if (distance < bestDistance) {
          bestDistance = distance;
          bestIndex = index;
        }
      });

      setActiveIndex(bestIndex);
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", handleScroll);

    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleScroll);
    };
  }, [containerRef, sectionCount]);

  return activeIndex;
}
