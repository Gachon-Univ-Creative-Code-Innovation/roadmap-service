from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.Roadmap.CrawlingToText import GetRoadmapDf
from src.Utils.RepoToDB import UploadRoadmap
from src.Utils.RepoToStorage import UploadSvgToStorage
from pyppeteer import launch
import datetime
import asyncio
import os

df = GetRoadmapDf()
scheduler = BackgroundScheduler()

# 로드맵 재로드를 하는 스케줄러 실행
def scheduled_job():
    print(f"[{datetime.datetime.now()}] [스케줄러] 로드맵 재로드 실행")
    global df
    df = GetRoadmapDf()
    print(df.head())

# 스케줄러 시작 함수
def start_scheduler():
    """매일 새벽 3시 정각에 작업 실행 (서버 시간 기준)"""
    trigger = CronTrigger(minute="*/1") # hour=3, minute=0
    scheduler.add_job(scheduled_job, trigger)
    scheduler.start()

# 스케줄러 시작
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduled_job()
    start_scheduler()
    yield

app = FastAPI(title="Roadmap Service API", lifespan=lifespan)

# CORS 설정 (필요시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# health check
@app.get("/api/roadmap/health-check")
async def healthCcheck():
    return {"status":200, "message": "서버 상태 확인", "data" :"working"}

# favicon 요청 무시 -> 로드맵 서비스는 favicon을 제공하지 않음
## favicon.ico는 웹사이트에 접속하면 자동으로 요청하는 파일임
@app.get("/api/roadmap/favicon.ico")
def favicon():
    return {
        "status" : 400,
        "message": "No favicon"
    }


# 전체 로드맵 리스트 반환
@app.get("/api/roadmap")
def ReadAllRoadmaps():
    """전체 로드맵 리스트 반환"""
    try:
        records = df.to_dict('records')

        return {
                "status": "200",
                "message": "전체 로드맵 리스트를 성공적으로 불러왔습니다.",
                "data": records
            }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "500",
                "message": f"로드맵 리스트 조회 실패: {str(e)}",
                "data": None
            }
        )

# 로드맵 데이터를 우리가 보기 위한 코드
@app.get("/api/roadmap/{urlName}")
async def GetRoadmapSvg(urlName: str):
    """SVG 파일을 실시간으로 생성하여 응답"""
    roadmapDf = df[df['urlName'] == urlName]
    if roadmapDf.empty:
        return JSONResponse(
            status_code = 404,
            content = {
                "status": "404",
                "message": f"로드맵을 찾을 수 없습니다: https://roadmap.sh/{urlName}",
                "data": None
            }
        )

    url = f"https://roadmap.sh/{urlName}"

    try:
        browser = await launch(headless = True)
        page = await browser.newPage()
        await page.setViewport({'width': 1980, 'height':1080})
        await page.goto(url, {'waitUntil': 'load', 'timeout':180000})

        svgElement = None
        for _ in range(60):
            svgElement = await page.querySelector('#resource-svg-wrap svg')
            if svgElement:
                break
            await asyncio.sleep(1)

        if not svgElement:
            await browser.close()
            return JSONResponse(
                status_code = 404,
                content = {
                    "status": "404",
                    "message": "SVG 요소를 찾을 수 없습니다.",
                    "data": None
                }
            )
        svgHtml = await page.evaluate('(element) => element.outerHTML', svgElement)
        await browser.close()
        return {
            "status": "200",
            "message": "로드맵 SVG가 생성되었습니다.",
            "data": svgHtml
        }

    except Exception as e:
        return JSONResponse(
            status_code= 500,
            content = {
                "status": "500",
                "message": f"로드맵 SVG 생성 실패: {e}",
                "data": None
            }
        )
@app.post("/api/roadmap/save/{url_name}")
async def SaveRoadmapSvg(urlName: str):
    """SVG파일을 roadmap.sh에서 크롤링하고 Supabase에 저장"""
    # 로드맵 이름 조회
    roadmapDf = df[df['urlName'] ==urlName]
    if roadmapDf.empty:
        return JSONResponse(
            status_code = 404,
            content = {
                "status": "404",
                "message": f"로드맵을 찾을 수 없습니다: https://roadmap.sh/{urlName}",
                "data": None
            }
        )
    roadmapName = roadmapDf.iloc[0]['roadmapName']
    url = f"https://roadmap.sh/{urlName}"

    try:
        # pyppeteer로 웹 페이지 접근 및 SVG 추출
        browser = await launch(headless=True)
        page = await browser.newPage()
        await page.setViewport({'width': 1980, 'height': 1080})
        await page.goto(url, {'waitUntil': 'load', 'timeout': 180000})

        svgElement = None
        for _ in range(60):
            svgElement = await page.querySelector('#resource-svg-wrap svg')
            if svgElement:
                break
            await asyncio.sleep(1)

        if not svgElement:
            await browser.close()
            return JSONResponse(
                status_code=404,
                content={
                    "status": "404",
                    "message": "SVG 요소를 찾을 수 없습니다.",
                    "data": None
                }
            )
        svgHtml = await page.evaluate('(element) => element.outerHTML', svgElement)
        # SVG 파일 로컬 저장
        fileName = f"{roadmapName}Roadmap.svg"
        localPath = f"/tmp/{fileName}"
        with open(localPath, 'w', encoding='utf-8') as f:
            f.write(svgHtml)

        await browser.close()

        # Supabase 스토리지에 SVG 업로드
        UploadSvgToStorage(filename=fileName, local_path=localPath)

        # Supabase DB에 메타데이터 저장
        roadmapData = {
            "urlName": urlName,
            "svgPath": fileName,
            "description": roadmapName
        }
        UploadRoadmap(roadmapData)

        # 로컬 파일 삭제
        os.remove(fileName)

        return {
            "status": "200",
            "message": f"로드맵 SVG가 Supabase에 저장되었습니다: {fileName}.",
                "data" : None

        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "500",
                "message": f"로드맵 SVG 저장 실패: {e}",
                "data": None
            }
        )


    # 태그 + 깃허브 요청하는코드(api top_k)
    # Alice cloude에 태그와 깃허브, 로드맵 리스트를 보내서 가장 잘 어울리는 로드맵 추천

    ##### 로드맵 이름이랑 url을 받으면 rdb supabseUrl을 다시 던져주기