import React from "react";
import "./WelcomePage.css";

const SUMMARY_TEXT =
  " AI 정밀 분석 결과: 관련 특허 총 6건 중 최적 매칭 5건 리스트업";

type PatentItem = {
  number: string;
  title: string;
  snippet: string;
  contextScore: number;
  reason: string;
  highlights?: string[];
  tag: string;
};

const PATENT_ITEMS: ReadonlyArray<PatentItem> = [
  {
    number: "10-2017-0003351",
    title: "거푸집 용 발열 필름, 및 이를 포함하는 발열 거푸집",
    snippet:
      "겨울철 콘크리트 양생 및 동결 방지를 위해 거푸집 내부에 발열 필름을 배치하는 구조를 제안합니다.",
    contextScore: 99.2,
    highlights: ["겨울철 콘크리트 양생", "동결 방지", "발열 필름"],
    reason:
      "겨울철 콘크리트 양생 및 동결 방지라는 사용자의 의도와 핵심 기술이 사실상 100% 일치하는 최적 매칭 특허입니다.",
    tag: "구조 분석 완료",
  },
  {
    number: "10-2017-0055620",
    title: "강재표면의 방청효과 및 아크 용사공법에 의한... 부착증강제",
    snippet:
      "거푸집 강재 표면의 방청 및 부착 성능을 향상시키기 위한 아크 용사 기반 부착증강제 기술입니다.",
    contextScore: 85.7,
    reason:
      "거푸집 강재의 내구성 및 부착력 강화와 직접적으로 연결되어, 보수·유지 측면에서 높은 점수를 받은 관련 기술입니다.",
    tag: "구조 분석 완료",
  },
  {
    number: "10-2017-0068973",
    title: "철근 콘크리트 부재 내 열화인자 확산 모니터링 장치 및 방법",
    snippet:
      "철근 콘크리트 부재 내 염해·열화 인자의 확산을 계측·모니터링하는 장치 및 방법을 제안합니다.",
    contextScore: 72.4,
    reason:
      "콘크리트 부식 및 열화 모니터링 기술로, 거푸집을 포함한 구조물의 사후 관리 프로세스에 적합하여 기술적 연관성이 있다고 판단됩니다.",
    tag: "구조 분석 완료",
  },
  {
    number: "20-2016-0005818",
    title: "손잡이 달린 필터 및 그 보관 용기",
    snippet:
      "손잡이가 부착된 필터와 이를 보관하기 위한 용기를 포함하는 생활 잡화 제품입니다.",
    contextScore: 15.2,
    reason:
      "'거푸집'과 직접적인 구조·재료 관점의 교집합이 부족하여, AI에 의해 낮은 연관성으로 재배치된 후보입니다.",
    tag: "도메인 불일치",
  },
  {
    number: "20-2024-0001732",
    title: "한 손으로 지퍼를 열고 닫을 수 있도록 보조하는 지퍼 고정 장치",
    snippet:
      "의류나 가방의 지퍼를 한 손으로 조작할 수 있도록 돕는 보조 장치에 관한 생활 편의 발명입니다.",
    contextScore: 8.4,
    reason:
      "사용자 질문의 '건설/거푸집' 도메인과 무관한 생활 잡화 기술로, 검색 파이프라인의 후순위로 필터링되었습니다.",
    tag: "도메인 불일치",
  },
];

function renderSnippet(item: PatentItem): React.ReactNode {
  if (!item.highlights || item.highlights.length === 0) {
    return item.snippet;
  }

  const parts: React.ReactNode[] = [];
  let remaining = item.snippet;
  let key = 0;

  // 간단한 다중 키워드 하이라이트
  while (remaining.length > 0) {
    const indices = item.highlights
      .map((h) => ({ h, idx: remaining.indexOf(h) }))
      .filter(({ idx }) => idx >= 0);

    if (indices.length === 0) {
      parts.push(remaining);
      break;
    }

    const { h, idx } = indices.reduce((best, cur) =>
      cur.idx < best.idx ? cur : best
    );

    if (idx > 0) {
      parts.push(remaining.slice(0, idx));
    }
    parts.push(
      <span key={`hl-${key}`} className="linkai-hybrid-snippet-highlight">
        {h}
      </span>
    );
    key += 1;
    remaining = remaining.slice(idx + h.length);
  }

  return parts;
}

/**
 * 2단계 하이브리드 검색 엔진: 딥러닝 기반 재랭킹 리포트 뷰어.
 */
export default function HybridSearchReport(): React.ReactElement {
  return (
    <div className="linkai-hybrid-report">
      <div className="linkai-hybrid-report-summary">
        {SUMMARY_TEXT}
        <span className="linkai-hybrid-summary-scoring">
          실시간 분석 스코어링
          <span className="linkai-hybrid-summary-dots" aria-hidden>
            …
          </span>
        </span>
      </div>
      <ul className="linkai-hybrid-report-list">
        {PATENT_ITEMS.map((item, index) => (
          <li
            key={item.number}
            className={
              index <= 2
                ? "linkai-hybrid-report-card is-top"
                : "linkai-hybrid-report-card is-low"
            }
          >
            <div className="linkai-hybrid-report-card-scores">
              <span className="linkai-hybrid-score-badge is-context">
                맥락 일치도 {item.contextScore.toFixed(1)}%
              </span>
            </div>

            <div className="linkai-hybrid-report-card-number">
              {item.number}
            </div>
            <div className="linkai-hybrid-report-card-title">
              {item.title}
            </div>
            <p className="linkai-hybrid-report-card-snippet">
              {renderSnippet(item)}
            </p>

            <div className="linkai-hybrid-reason">
              <div className="linkai-hybrid-reason-label">
                AI 판단 근거 · {item.tag}
              </div>
              <p className="linkai-hybrid-reason-text">{item.reason}</p>
            </div>

            {index < PATENT_ITEMS.length - 1 && (
              <span
                className="linkai-hybrid-flow-indicator"
                aria-hidden
              />
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
