import React, { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import "./WelcomePage.css";

const USER_MSG = "기존 거푸집 문제를 해결하는 특허가 있을까?";
const THINKING_MSG =
  "질문을 분석 중입니다... 거푸집 문제를 계절·환경·재료 관점에서 분해하고 있어요.";

const ANSWER_LINES: string[] = [
  "[의도 파악] '거푸집 문제'를 겨울철 콘크리트 양생 및 동결 방지 이슈로 구조화 완료",
  "[기술 매칭] '발열 필름' 및 '저온 환경 동결 방지 거푸집' 핵심 키워드 추출",
  "검색 결과 요약: 거푸집 용 발열 필름 및 관련 특허 총 6건 탐색 완료",
];

const USER_TYPING_MS = 58;
const THINKING_DURATION_MS = 2000;
const HOLD_AFTER_ANSWER_MS = 5200;
const RESET_BEFORE_LOOP_MS = 900;
const ANSWER_LINE_INTERVAL_MS = 400;

type Phase = "idle" | "userTyping" | "thinking" | "answer" | "hold";

interface AIEngineDemoChatProps {
  /** When true, start or continue the demo animation (scroll in or hover). */
  trigger: boolean;
}

export default function AIEngineDemoChat({
  trigger,
}: AIEngineDemoChatProps): React.ReactElement {
  const [phase, setPhase] = useState<Phase>("idle");
  const [userLen, setUserLen] = useState(0);
  const [visibleAnswerLines, setVisibleAnswerLines] = useState(0);
  const hasCompletedOnce = useRef(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = useCallback(() => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current = [];
  }, []);

  const reset = useCallback(() => {
    setPhase("idle");
    setUserLen(0);
    setVisibleAnswerLines(0);
  }, []);

  useEffect(() => {
    if (!trigger) {
      clearTimers();
      reset();
      hasCompletedOnce.current = false;
      return;
    }

    const runUserTyping = () => {
      setPhase("userTyping");
      setUserLen(0);
      let n = 0;
      const run = () => {
        if (n < USER_MSG.length) {
          n += 1;
          setUserLen(n);
          const t = setTimeout(run, USER_TYPING_MS);
          timers.current.push(t);
        } else {
          setPhase("thinking");
          const t = setTimeout(() => {
            setPhase("answer");
            setVisibleAnswerLines(0);

            ANSWER_LINES.forEach((_, idx) => {
              const tLine = setTimeout(() => {
                setVisibleAnswerLines((prev) =>
                  Math.min(prev + 1, ANSWER_LINES.length)
                );
              }, idx * ANSWER_LINE_INTERVAL_MS);
              timers.current.push(tLine);
            });

            const tDone = setTimeout(() => {
              setPhase("hold");
              const tLoop = setTimeout(() => {
                reset();
                hasCompletedOnce.current = true;
                runUserTyping();
              }, RESET_BEFORE_LOOP_MS);
              timers.current.push(tLoop);
            }, HOLD_AFTER_ANSWER_MS);
            timers.current.push(tDone);
          }, THINKING_DURATION_MS);
          timers.current.push(t);
        }
      };
      run();
    };

    if (phase === "idle" && !hasCompletedOnce.current) {
      runUserTyping();
    }
  }, [trigger, phase, reset, clearTimers]);

  const showUser = phase !== "idle";
  const showThinking = phase === "thinking";
  const showAnswer = phase === "answer" || phase === "hold";

  return (
    <div className="linkai-demo-chat">
      {showUser && (
        <motion.div
          className="linkai-demo-chat-row linkai-demo-chat-row-user"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <div className="linkai-demo-chat-bubble linkai-demo-chat-bubble-user">
            <div className="linkai-demo-chat-bubble-inner">
              {USER_MSG.slice(0, userLen)}
            </div>
          </div>
        </motion.div>
      )}

      {showThinking && (
        <motion.div
          className="linkai-demo-chat-row linkai-demo-chat-row-bot"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          <div className="linkai-demo-chat-thinking">
            <div className="linkai-demo-chat-thinking-skeleton" aria-hidden />
            <span className="linkai-demo-chat-thinking-text">{THINKING_MSG}</span>
          </div>
        </motion.div>
      )}

      {showAnswer && (
        <motion.div
          className="linkai-demo-chat-row linkai-demo-chat-row-bot"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.35 }}
        >
          <div className="linkai-demo-chat-bubble linkai-demo-chat-bubble-bot">
            <div className="linkai-demo-chat-bubble-inner linkai-demo-chat-answer-inner">
              {ANSWER_LINES.slice(0, visibleAnswerLines).map((line, idx) => (
                <motion.div
                  key={line}
                  className="linkai-demo-answer-line"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25 }}
                >
                  {idx === 0 && (
                    <span
                      className="linkai-demo-answer-spinner"
                      aria-hidden
                    />
                  )}
                  <span className="linkai-demo-answer-text">{line}</span>
                </motion.div>
              ))}
              {visibleAnswerLines === ANSWER_LINES.length && (
                <button
                  type="button"
                  className="linkai-demo-answer-detail-button"
                >
                  상세 리스트 보기
                </button>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
