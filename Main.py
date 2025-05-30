from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.Roadmap.CrawlingToText import GetRoadmapDf
from src.Utils.RepoToDB import UploadRoadmap,ReadRoadmapList,UpdateRoadmap,ClearRoadmap
from src.Utils.RepoToStorage import UploadStorage,ClearStorage
from pyppeteer import launch
import traceback
import datetime
import asyncio
import httpx
import os

df = GetRoadmapDf()
scheduler = BackgroundScheduler()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")

# 로드맵 재로드를 하는 스케줄러 실행
def scheduled_job():
    print(f"[{datetime.datetime.now()}] [스케줄러] 로드맵 재로드 실행")
    global df
    df = GetRoadmapDf()
    try:
        SaveRoadmaps()
        loop = asyncio.get_event_loop()
        loop.create_task(SaveRoadmapSvg())
        print("[스케줄러] DB 및 SVG 저장 완료")
    except Exception as e:
        print(f"[스케줄러 오류] {e}")


# 스케줄러 시작 함수
def start_scheduler():
    """매일 새벽 3시 정각에 작업 실행 (서버 시간 기준)"""
    if scheduler.running:
        print("[스케줄러] 이미 실행 중입니다.")
        return

    trigger = CronTrigger(hour=3, minute=0)
    scheduler.add_job(scheduled_job, trigger)
    scheduler.start()
    print("[스케줄러] 시작 완료")

# 스케줄러 시작
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[앱 시작] 초기 로드맵 재로드 및 스케줄러 실행")
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

# 크롤링한 로드맵 데이터를 supabae DB에 저장
@app.post("/api/roadmap/save")
def SaveRoadmaps():
    try:
        df = GetRoadmapDf() # 크롤링한 로드맵 데이터프레임
        records = []

        ClearRoadmap()

        for _, row in df.iterrows():
            data  = {
                "roadmapType": row['roadmapType'],
                "roadmapName": row['roadmapName'],
                "roadmapUrl": row['urlName'],
                "svgUrl": None,
                "userId": 1,  # 기본값 1로 설정
            }

            UploadRoadmap(data)
            records.append(data)

        return{
            "status": "200",
            "message": "로드맵 데이터를 성공적으로 Supabase DB에 저장했습니다.",
            "data": records
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "500",
                "message": f"로드맵 데이터 저장 실패: {str(e)}",
                "data": None
            }
        )


# 전체 로드맵 리스트 반환
@app.get("/api/roadmap")
def ReadAllRoadmaps():
    """전체 로드맵 리스트 반환"""
    try:
        records = ReadRoadmapList()

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

# 로드맵 SVG 파일을 Supabase에 저장
@app.post("/api/roadmap/saveSvg")
async def SaveRoadmapSvg():
    """SVG파일을 roadmap.sh에서 크롤링하고 Supabase에 저장"""
    records = ReadRoadmapList()
    results = []

    try:
        ClearStorage()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "500",
                "message": f"스토리지 초기화 실패: {e}",
                "data": None
            }
        )

    try:
        # pyppeteer로 웹 페이지 접근 및 SVG 추출
        browser = await launch(
            headless=True,
            executablePath='/usr/bin/chromium',
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-zygote"
            ]
        )

        for record in records:
            urlName = record['roadmapUrl']
            roadmapName = record['roadmapName']
            url = f"https://roadmap.sh/{urlName}"

            if not urlName:
                results.append({
                    "roadmapName": roadmapName,
                    "status": "로드맵 URL 없음",
                    "svgUrl": None
                })
                continue

            try:
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
                    results.append({
                        "roadmapName": roadmapName,
                        "status": "SVG 요소 없음",
                        "svgUrl": None
                    })
                    continue

                svgHtml = await page.evaluate('(element) => element.outerHTML', svgElement)
                # SVG 파일 로컬 저장
                fileName = f"{roadmapName}Roadmap.svg"
                localPath = f"/tmp/{fileName}"
                with open(localPath, 'w', encoding='utf-8') as f:
                    f.write(svgHtml)

                # Supabase 스토리지에 SVG 업로드
                UploadStorage(filename=fileName, local_path=localPath)

                # Supabase DB에 메타데이터 저장
                svgUrl = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{fileName}"
                UpdateRoadmap(roadmapName=roadmapName, svgUrl=svgUrl)

                results.append({
                    "roadmapName": roadmapName,
                    "status": "업로드 완료",
                    "svgUrl": svgUrl
                })

                await asyncio.sleep(1)
                await page.close()

            except Exception as e:
                traceback.print_exc()
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "500",
                        "message": f"로드맵 SVG 저장 실패: {e}",
                        "svgUrl": None
                    })
                continue

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "500",
                "message": f"브라우저 실행 실패: {e}",
                "data": None
            }
        )
    finally:
        await browser.close()

    return {
        "status": "200",
        "message": f"로드맵 SVG가 Supabase에 저장되었습니다.",
        "data": results

    }

# supabase에 저장되어 있는 로드맵 svg파일을 보여줌
@app.get("/api/roadmap/svgView")
async def GetRoadmapSvg(roadmapName: str):
        """로드맵 이름 기준으로 SVG URL을 반환"""
        records = ReadRoadmapList()
        matched = next((r for r in records if r["roadmapName"] == roadmapName), None)
        try:
            if not matched:
                return {
                    "status": "404",
                    "message": f"해당 로드맵 이름({roadmapName})을 찾을 수 없습니다.",
                    "data": None
                }

            svgUrl = matched.get("svgUrl")
            if not svgUrl:
                return {
                    "status": "404",
                    "message": "로드맵이 존재하지 않습니다.",
                    "data": None
                }

            async with httpx.AsyncClient() as client:
                response = await client.get(svgUrl)

            if response.status_code != 200:
                return {
                    "status": "500",
                    "message": f"SVG 파일을 가져오는 데 실패했습니다. 상태코드: {response.status_code}",
                    "data": None
                }

            return Response(
                content=response.content,
                media_type="image/svg+xml"
            )

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "500",
                    "message": f"로드맵 SVG URL 조회 실패: {e}",
                    "data": None
                }
            )

# 태그 + 깃허브 요청하는코드(api top_k)
# Alice cloude에 태그와 깃허브, 로드맵 리스트를 보내서 가장 잘 어울리는 로드맵 추천

##### 로드맵 이름이랑 url을 받으면 rdb supabseUrl을 다시 던져주기