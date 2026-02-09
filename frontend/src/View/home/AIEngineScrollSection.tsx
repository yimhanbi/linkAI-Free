import React, { useRef, useState } from "react";
import { Layers, Database, FileSearch, ShieldCheck } from "lucide-react";
import { useScrollReactiveSections } from "./useScrollReactiveSections";
import AIEngineDemoChat from "./AIEngineDemoChat";
import HybridSearchReport from "./HybridSearchReport";
import ClaimDeepDiveViewer from "./ClaimDeepDiveViewer";
import RAGReportViewer from "./RAGReportViewer";
import "./WelcomePage.css";

const LEFT_ITEMS: { label: string; body: string }[] = [
  {
    label: "지능형 하이브리드 검색",
    body: "벡터 임베딩을 통한 맥락 검색과 메타데이터 기반의 가중치 정밀 검색을 결합하여 단 하나의 관련 특허도 놓치지 않습니다.",
  },
  {
    label: "딥러닝 기반 정밀 Reranking",
    body: "AI가 검색된 후보들을 질문의 의도와 대조하여 정밀하게\n Reranking함으로써 비즈니스 목적에 가장 부합하는 최적의 특허만을 선별합니다.",
  },
  {
    label: "청구항 중심의 권리 분석",
    body: "요약문을 넘어 특허의 핵심인 '청구항' 전체를 심층 분석함으로써,\n 사용자의 질문이 실제 특허 권리 범위와 얼마나 일치하는지\n 맥락적으로 추론합니다.",
  },
  {
    label: "근거 기반의 출처 보증",
    body: "분석된 수많은 특허 데이터를 근거(Context)로 삼아, 외부 지식 섞임 없는 가장 정확한 분석 결과를 제공합니다.",
  },
];

const RIGHT_BLOCKS: ReadonlyArray<{
  title: string;
  content: string;
  Icon: React.ComponentType<{ className?: string; size?: number }>;
}> = [
  {
    title: "지능형 하이브리드 검색",
    content:
      "사용자의 추상적인 질문을 분석하여 최적의 기술 키워드로 변환하고, 관련 특허를 정밀하게 추적합니다.",
    Icon: Layers,
  },
  {
    title: "딥러닝 기반 정밀 Reranking",
    content:
    "AI가 검색된 후보들을 질문의 의도와 대조하여 정밀하게\n재채점함으로써 비즈니스 목적에 가장 부합하는 최적의 특허만을\n선별합니다.",
    Icon: Database,
  },
  {
    title: "청구항 중심의 권리 분석",
    content:
      "요약문을 넘어 특허의 핵심인 '청구항' 전체를 심층 분석하여, 사용자의 질문이 실제 특허 권리 범위와 얼마나 일치하는지 맥락적으로 추론합니다.",
    Icon: FileSearch,
  },
  {
    title: "근거 기반의 출처 보증",
    content:
     "분석된 수많은 특허 데이터를 근거(Context)로 삼아, 외부 지식 섞임 없는 가장 정확한 분석 결과를 제공합니다.",
    Icon: ShieldCheck,
  },
];

export default function AIEngineScrollSection(): React.ReactElement {
  const rightColumnRef = useRef<HTMLDivElement>(null);
  const activeIndex = useScrollReactiveSections(rightColumnRef, LEFT_ITEMS.length);
  const [demoHovered, setDemoHovered] = useState(false);
  const demoTrigger = activeIndex === 0 || demoHovered;

  return (
    <div className="linkai-scroll-reactive">
      <div className="linkai-scroll-reactive-inner">
        <aside className="linkai-scroll-reactive-left">
          {LEFT_ITEMS.map((item, i) => (
            <div
              key={item.label}
              className="linkai-scroll-reactive-item"
              data-active={i === activeIndex ? "true" : "false"}
            >
              <div className="linkai-scroll-reactive-item-label">
                {item.label}
              </div>
              <div className="linkai-scroll-reactive-item-body">{item.body}</div>
            </div>
          ))}
        </aside>
        <div
          ref={rightColumnRef}
          className="linkai-scroll-reactive-right"
          role="region"
          aria-label="AI Engine 설명"
        >
          {RIGHT_BLOCKS.map((block, i) => {
            const isActive = i === activeIndex;
            const { Icon } = block;
            const isFirstBlock = i === 0;
            return (
              <section
                key={block.title}
                className="linkai-scroll-reactive-block"
                data-scroll-section
                data-active={isActive ? "true" : "false"}
                onMouseEnter={isFirstBlock ? () => setDemoHovered(true) : undefined}
                onMouseLeave={isFirstBlock ? () => setDemoHovered(false) : undefined}
              >
                <div
                  className="linkai-scroll-reactive-block-icon"
                  data-active={isActive ? "true" : "false"}
                  aria-hidden
                >
                  <Icon className="linkai-scroll-reactive-block-icon-svg" size={32} />
                </div>
                <h3 className="linkai-scroll-reactive-block-title">
                  {block.title}
                </h3>
                {isFirstBlock ? (
                  <>
                    <div className="linkai-demo-chat-wrap">
                      <AIEngineDemoChat trigger={demoTrigger} />
                    </div>
                    <div className="linkai-hybrid-tags" aria-hidden>
                      <span className="linkai-hybrid-tag">🔍 기술 의도 확장</span>
                      <span className="linkai-hybrid-tag">🆔 키워드 구조화</span>
                      <span className="linkai-hybrid-tag">⚡ 하이브리드 탐색</span>
                    </div>
                  </>
                ) : i === 1 ? (
                  <HybridSearchReport />
                ) : i === 2 ? (
                  <ClaimDeepDiveViewer />
                ) : i === 3 ? (
                  <RAGReportViewer />
                ) : (
                  <p className="linkai-scroll-reactive-block-content">
                    {block.content}
                  </p>
                )}
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}
