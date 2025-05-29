# Python 3.9 이상 이미지 사용
FROM python:3.9-slim

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libgtk-3-0 \
    libglib2.0-0 \
    libnss3 \
    libxss1 \
    libx11-6 \
    wget \
    unzip \
    curl \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# 환경 변수 설정
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/lib/chromium/chromedriver


# 작업 디렉터리 설정
WORKDIR /app

# 필요 파일 복사
COPY . .

# 위치 지정
ENV PYTHONPATH=/app


# 의존성 설치
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI 실행
CMD ["uvicorn", "Main:app", "--host", "0.0.0.0", "--port", "8000"]