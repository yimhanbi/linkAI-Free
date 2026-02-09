import React from "react";
import "./WelcomePage.css";

const TOP_BADGE_LABEL = "근거 기반 출처 보증";
const STATUS_TITLE =
  "AI가 거푸집 발열 필름 특허 데이터를 바탕으로 비즈니스 전략을 수립 중입니다.";

const USER_QUESTION =
  "거푸집 발열 필름 특허를 바탕으로 사업화 전략을 내줘";
const KEYWORD_TAGS = ["#거푸집_발열_필름", "#동결_방지", "#사업화_전략"];

const LOG_ENTRIES = [
  {
    status: "success" as const,
    text: "한양대 ERICA 특허 DB 매칭 완료 (유사도 99.2%)",
  },
  {
    status: "success" as const,
    text: "거푸집 용 발열 필름 외 5건 포트폴리오 로드 성공",
  },
  {
    status: "running" as const,
    text: "RAG 기반 수요처 매칭 및 라이선싱 모델 가동 중...",
  },
];

const GRAPH_QUERY_LABEL = "거푸집 발열 필름";
const GRAPH_NODE_LABEL = "비즈니스 수요처";
const GRAPH_EDGE_LABEL = "데이터 매칭 중";
const GRAPH_SIMILARITY = "0.99";

const INSIGHT_CARDS = [
  {
    label: "수요처 추천",
    body: "현대건설, DL이앤씨 등 대형 건설사 타겟팅 가능",
  },
  {
    label: "사업화 전략",
    body: "겨울철 공기 단축 솔루션 기반 기술 가치 평가 및 라이선싱 모델 제안",
  },
];
const CARD_BADGE_LABEL = "분석 기반 제안";

const FOOTER_TEXT =
  "본 리포트는 분석된 6건의 거푸집 특허 데이터를 기반으로 생성되었습니다.";

/**
 * 4단계: 근거 기반의 출처 보증 (Grounded Meta Injection).
 */
export default function RAGReportViewer(): React.ReactElement {
  return (
    <div className="linkai-rag-workspace">
      <div className="linkai-rag-workspace-top">
        <span className="linkai-rag-top-badge" aria-hidden>
          {TOP_BADGE_LABEL}
        </span>
        <p className="linkai-rag-workspace-title">
          {STATUS_TITLE}
          <span className="linkai-rag-status-cursor" aria-hidden />
        </p>
      </div>

      <div className="linkai-rag-workspace-body">
        {/* 1. 사용자 질문(말풍선) + 쿼리에서 추출한 키워드 */}
        <section className="linkai-rag-question-block" aria-label="내 질문">
          <div className="linkai-rag-question-bubble">
            <span className="linkai-rag-question-bubble-label">사용자 질문</span>
            <p className="linkai-rag-question-text">{USER_QUESTION}</p>
          </div>
          <p className="linkai-rag-keywords-caption">쿼리에서 추출된 키워드</p>
          <div className="linkai-rag-keywords">
            {KEYWORD_TAGS.map((tag) => (
              <span key={tag} className="linkai-rag-keyword-tag">
                {tag}
              </span>
            ))}
          </div>
        </section>

        {/* 2. 중앙: 분석 엔진 (터미널 + 관계도) */}
        <div className="linkai-rag-process-grid">
          <section
            className="linkai-rag-terminal"
            aria-label="분석 프로세스 로그"
          >
            <div className="linkai-rag-terminal-inner">
              {LOG_ENTRIES.map((entry, i) => (
                <div key={i} className="linkai-rag-log-line">
                  <span
                    className={
                      entry.status === "success"
                        ? "linkai-rag-log-dot linkai-rag-log-dot-success"
                        : "linkai-rag-log-dot linkai-rag-log-dot-running"
                    }
                    aria-hidden
                  />
                  <span className="linkai-rag-log-text">
                    &gt; {entry.text}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section
            className="linkai-rag-graph"
            aria-label="질문-발명자 데이터 연결"
          >
            <div className="linkai-rag-graph-inner linkai-rag-graph-single">
              <div className="linkai-rag-graph-node linkai-rag-graph-node-center">
                {GRAPH_QUERY_LABEL}
              </div>
              <div className="linkai-rag-graph-connection">
                <div className="linkai-rag-graph-edge-bold" aria-hidden />
                <span className="linkai-rag-graph-edge-mid-label">
                  {GRAPH_EDGE_LABEL}
                </span>
              </div>
              <div className="linkai-rag-graph-node linkai-rag-graph-node-outer">
                {GRAPH_NODE_LABEL}
              </div>
              <div className="linkai-rag-graph-similarity">
                Similarity: {GRAPH_SIMILARITY}
              </div>
            </div>
          </section>
        </div>

        {/* 3. 하단: 전략 수립 미리보기 */}
        <section
          className="linkai-rag-cards-wrap"
          aria-label="전략 카드 미리보기"
        >
          {INSIGHT_CARDS.map((card) => (
            <div key={card.label} className="linkai-rag-insight-card">
              <span className="linkai-rag-card-badge">
                {CARD_BADGE_LABEL}
              </span>
              <h5 className="linkai-rag-card-label">[{card.label}]</h5>
              <p className="linkai-rag-card-body">{card.body}</p>
            </div>
          ))}
        </section>
      </div>

      <footer className="linkai-rag-workspace-footer">{FOOTER_TEXT}</footer>
    </div>
  );
}
