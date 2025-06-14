# Python 3.9 이상 이미지 사용
FROM python:3.9-slim

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libgtk-3-0 \
    libglib2.0-0 \
    libnss3 \
    libxss1 \
    libx11-6 \
    wget \
    unzip \
    curl \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    libpq-dev \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# 환경 변수 설정
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/lib/chromium/chromedriver
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium


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
CMD ["uvicorn", "Main:app", "--host", "0.0.0.0", "--port", "8080"]