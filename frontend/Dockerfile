FROM node:18-alpine

WORKDIR /app

# 1) 프론트엔드 패키지 설치
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# 2) 소스 복사 및 빌드
COPY frontend/ .

# docker-compose 에서 전달하는 빌드 아규먼트와 연동
ARG VITE_BACKEND_URL
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}

RUN npm run build

EXPOSE 3000

# 개발/프리뷰 용: 컨테이너에서 Vite 서버 실행
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]