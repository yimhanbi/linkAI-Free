import React from "react";
import { FileSearch } from "lucide-react";
import "./WelcomePage.css";

type HighlightVariant = "blue" | "green" | "amber" | "none";

const CLAIM_PART = (
  text: string,
  variant: HighlightVariant = "none",
  label?: string
) => ({ text, variant, label } as const);

const ANALYSIS_BLOCKS: ReadonlyArray<{
  header: string;
  claimParts: ReadonlyArray<{
    text: string;
    variant: HighlightVariant;
    label?: string;
  }>;
  insights: ReadonlyArray<{ title: string; body: string }>;
  conclusion: string;
}> = [
  {
    header:
      "[분석 중] 10-2017-0003351: 거푸집 용 발열 필름, 및 이를 포함하는 발열 거푸집",
    claimParts: [
      CLAIM_PART("청구항 제1항: "),
      CLAIM_PART("발열체", "blue", "핵심 발열 모듈"),
      CLAIM_PART("와, 상기 발열체에 전원을 공급하는 전극선 및 이를 감싸는 "),
      CLAIM_PART("절연 필름", "green", "안전·내구성 요소"),
      CLAIM_PART(
        "을 포함하며, 저온 환경에서 콘크리트의 ",
        "none"
      ),
      CLAIM_PART("초기 동결 방지", "amber", "동절기 시공 핵심 기능"),
      CLAIM_PART(
        "를 가능하게 하는 것을 특징으로 하는 발열 거푸집."
      ),
    ],
    insights: [
      {
        title: "권리 범위 분석",
        body: "단순 발열 장치가 아닌 '절연 필름 일체형 거푸집'으로 청구되어, 발열체·절연 구조를 모두 포함하는 광범위한 독점 권리를 형성합니다.",
      },
      {
        title: "기술적 차별성",
        body: "기존 외부 가열 방식 대비 저전력으로 콘크리트 심부 온도를 유지하는 구조·제어 알고리즘을 결합하여, 동절기 시공 품질을 안정적으로 확보합니다.",
      },
    ],
    conclusion:
      "본 청구항은 동절기 공기 단축 및 품질 관리 측면에서 강력한 기술적 해법을 제시합니다.",
  },
];

function ClaimAnalysisBlock({
  header,
  claimParts,
  insights,
  conclusion,
}: (typeof ANALYSIS_BLOCKS)[number]): React.ReactElement {
  return (
    <div className="linkai-claim-block">
      <div className="linkai-claim-viewer-header">
        <FileSearch className="linkai-claim-viewer-header-icon" size={18} aria-hidden />
        <span className="linkai-claim-viewer-header-text">{header}</span>
      </div>

      <div className="linkai-claim-viewer-split">
        <div className="linkai-claim-viewer-original">
          <div className="linkai-claim-viewer-original-label">원문</div>
          <div className="linkai-claim-viewer-claim-text">
            {claimParts.map((part, idx) =>
              part.variant !== "none" ? (
                <span key={idx} className="linkai-claim-highlight-wrap">
                  <span
                    className={`linkai-claim-highlight linkai-claim-highlight--${part.variant}`}
                  >
                    {part.text}
                  </span>
                  {part.label && (
                    <span className="linkai-claim-annotation">{part.label}</span>
                  )}
                </span>
              ) : (
                <span key={idx}>{part.text}</span>
              )
            )}
          </div>
        </div>
        <div className="linkai-claim-viewer-insights">
          <div className="linkai-claim-viewer-insights-label">인사이트 요약</div>
          {insights.map((item) => (
            <div key={item.title} className="linkai-claim-insight-card">
              <div className="linkai-claim-insight-card-title">[{item.title}]</div>
              <p className="linkai-claim-insight-card-body">{item.body}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="linkai-claim-viewer-conclusion">
        <p className="linkai-claim-viewer-conclusion-text">{conclusion}</p>
      </div>
    </div>
  );
}

/**
 * 3단계 청구항 중심 맥락 추론: 심층 분석 뷰어 (정적, 애니메이션 없음).
 */
export default function ClaimDeepDiveViewer(): React.ReactElement {
  return (
    <div className="linkai-claim-viewer">
      {ANALYSIS_BLOCKS.map((block, idx) => (
        <ClaimAnalysisBlock key={idx} {...block} />
      ))}
    </div>
  );
}
