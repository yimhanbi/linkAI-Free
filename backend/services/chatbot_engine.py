import os
import time
import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorClient
from backend.services import search_service

class ChatbotEngine:
    """특허 검색 챗봇 엔진 - 세션 관리 및 RAG 로직 연동"""
    
    def __init__(self):
        self._initialized = False
        
        # MongoDB 설정 (환경 변수 기본값 처리)
        self.mongo_uri = os.getenv("MONGO_URI")
        self.db_name = os.getenv("DB_NAME")
        self.chat_history_ttl_days = int(os.getenv("CHAT_HISTORY_TTL_DAYS", "30"))
        
        # MongoDB 클라이언트 초기화
        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client[self.db_name]
        
        # 인덱스 생성 여부 확인 플래그
        self._indexes_ensured = False

    # --------------------------------------
    # 답변 생성 로직 (RAG 서비스 호출)
    # --------------------------------------

    async def answer(
        self, 
        query: str, 
        session_id: Optional[str] = None,
        top_k: int = 30,
    ) -> dict:
        """기본 RAG 답변 생성 및 메시지 저장"""
        # MongoDB 인덱스 자동 확인
        await self._ensure_indexes_once()
        
        # 1. 세션 ID가 없으면 새로 생성
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 2. 성능 측정을 위한 시작 시간
        start_time = time.time()
        
        # 3. RAG 답변 생성 (search_service의 비동기 함수 호출)
        # 주의: search_service에 hybrid_rag_answer 함수가 정의되어 있어야 합니다.
        answer,sources = await search_service.run_llamaindex_query(query, top_k=top_k)
        
        # 4. 처리 시간 계산
        query_time = time.time() - start_time
        
        # 5. MongoDB 대화 내역에 저장
        await self.save_message(session_id, query, answer)
        
        # 6. 최종 응답 객체 반환
        return {
            "answer": answer,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "query_time": round(query_time, 2),
                "top_k": top_k
            }
        }

    async def answer_with_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 30
    ) -> dict:
        """이전 대화 내역을 참고하여 답변 생성 (대화 맥락 유지)"""
        # 1. 이전 대화 내역 조회
        history = await self.get_chat_history(session_id)
        
        # 2. 최근 3개 문답(최대 6개 메시지)만 컨텍스트로 사용
        recent_messages = history[-6:] if len(history) > 6 else history
        
        context = ""
        for msg in recent_messages:
            role = "사용자" if msg.get("role") == "user" else "어시스턴트"
            context += f"{role}: {msg.get('content')}\n"
        
        # 3. 컨텍스트를 주입한 강화된 쿼리 생성
        enhanced_query = f"""이전 대화 맥락:
{context}
현재 질문: {query}

위 대화 내용을 바탕으로 자연스럽게 답변해줘."""
        
        # 4. 기존 answer 메서드 재사용
        return await self.answer(enhanced_query, session_id, top_k)

    # --------------------------------------
    # 세션 및 대화 내역 관리 (MongoDB)
    # --------------------------------------
    
    async def save_message(self, session_id: str, user_query: str, ai_answer: str) -> None:
        """대화 내용을 MongoDB에 업데이트 (Upsert)"""
        collection = self.db["chat_history"]
        now_dt = datetime.utcnow()
        
        # 세션 제목: 첫 질문이 너무 길면 자름
        title = (user_query[:25] + "...") if len(user_query) > 25 else user_query
        
        await collection.update_one(
            {"session_id": session_id},
            {
                "$setOnInsert": {
                    "session_id": session_id,
                    "created_at": now_dt,
                    "title": title,
                },
                "$push": {
                    "messages": {
                        "$each": [
                            {"role": "user", "content": user_query, "timestamp": time.time()},
                            {"role": "assistant", "content": ai_answer, "timestamp": time.time()},
                        ]
                    }
                },
                "$set": {
                    "updated_at": now_dt,
                    "expires_at": now_dt + timedelta(days=self.chat_history_ttl_days),
                },
            },
            upsert=True,
        )

    async def get_all_session(self, limit: int = 100) -> list:
        """모든 채팅 세션 목록 조회"""
        collection = self.db["chat_history"]
        cursor = collection.find(
            {}, 
            {"_id": 0, "session_id": 1, "title": 1, "updated_at": 1}
        ).sort("updated_at", -1).limit(limit)
        
        sessions = await cursor.to_list(length=limit)
        
        for session in sessions:
            if "updated_at" in session and isinstance(session["updated_at"], datetime):
                session["updated_at"] = int(session["updated_at"].timestamp() * 1000)
        return sessions

    async def get_chat_history(self, session_id: str) -> list:
        """특정 세션의 전체 메시지 내역 조회"""
        collection = self.db["chat_history"]
        doc = await collection.find_one({"session_id": session_id}, {"_id": 0, "messages": 1})
        if not doc:
            return []
        messages = doc.get("messages", [])
        return messages

    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        collection = self.db["chat_history"]
        result = await collection.delete_one({"session_id": session_id})
        return bool(result.deleted_count > 0)

    async def update_session_title(self, session_id: str, new_title: str) -> bool:
        """세션 제목 수동 변경"""
        collection = self.db["chat_history"]
        result = await collection.update_one(
            {"session_id": session_id},
            {"$set": {"title": new_title}}
        )
        return bool(result.modified_count > 0)

    async def get_session_statistics(self, session_id: str) -> dict:
        """세션 데이터 통계 조회 (메시지 수 등)"""
        collection = self.db["chat_history"]
        doc = await collection.find_one({"session_id": session_id})
        if not doc:
            return {}
        
        messages = doc.get("messages", [])
        created_at = doc.get("created_at")
        updated_at = doc.get("updated_at")
        duration = int((updated_at - created_at).total_seconds()) if created_at and updated_at else 0
        
        return {
            "message_count": len(messages),
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "duration_seconds": duration
        }

    # --------------------------------------
    # 인덱스 관리 (MongoDB 성능 최적화)
    # --------------------------------------
    
    async def _ensure_indexes_once(self):
        """런타임 중 인덱스 설정을 한 번만 수행하도록 보장"""
        if not self._indexes_ensured:
            await self._ensure_chat_history_indexes()
            self._indexes_ensured = True

    async def _ensure_chat_history_indexes(self) -> None:
        """조회 및 TTL 삭제를 위한 인덱스 생성"""
        try:
            collection = self.db["chat_history "]
            await collection.create_index([("session_id",1)], name = "chat_history_session_id_idx")
            
            await collection.create_index([("expires_at", 1)], expireAfterSeconds=0, name="chat_history_expires_at_ttl")
            print("✅ MongoDB indexes verified.")
        except Exception as e:
            print(f"⚠️ MongoDB index warning (can be ignored if already exists): {e}")
            