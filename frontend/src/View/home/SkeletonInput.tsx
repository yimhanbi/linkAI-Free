import React, { useRef, useEffect, useState } from "react";

interface SkeletonInputProps {
  value: string;
  onChange: (value: string) => void;
  onFocus?: () => void;
  onBlur?: () => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  placeholderNode: React.ReactNode;
  "aria-label"?: string;
}

/**
 * Hero input with transparent placeholder and a skeleton line that grows
 * with the typed text width. The visible "placeholder" is rendered via placeholderNode.
 */
export default function SkeletonInput({
  value,
  onChange,
  onFocus,
  onBlur,
  onKeyDown,
  placeholderNode,
  "aria-label": ariaLabel,
}: SkeletonInputProps): React.ReactElement {
  const measureRef = useRef<HTMLSpanElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [skeletonWidth, setSkeletonWidth] = useState(0);

  useEffect(() => {
    if (!measureRef.current) return;
    measureRef.current.textContent = value;
    const raf = requestAnimationFrame(() => {
      if (measureRef.current) setSkeletonWidth(measureRef.current.offsetWidth);
    });
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return (
    <div className="linkai-hero-input-wrap">
      <div className="linkai-hero-input-inner">
        <input
          ref={inputRef}
          type="text"
          className="linkai-hero-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={onFocus}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          placeholder=" "
          aria-label={ariaLabel}
        />
        <span
          ref={measureRef}
          className="linkai-hero-input-measure"
          aria-hidden
        />
        <span
          className="linkai-hero-input-skeleton"
          style={{ width: skeletonWidth }}
          aria-hidden
        />
        <span className="linkai-hero-input-placeholder" aria-hidden>
          {placeholderNode}
        </span>
      </div>
    </div>
  );
}
