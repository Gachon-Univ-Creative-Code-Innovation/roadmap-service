from fastapi import FastAPI, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.Roadmap.CrawlingToText import GetRoadmapDf
from src.Utils.RepoToDB import UploadRoadmap,ReadRoadmapList,UpdateRoadmap,ClearRoadmap,ReadRoadmapAllList
from src.Utils.RepoToStorage import UploadStorage,ClearStorage
from src.Utils.GetGWT import GetDataFromToken,GetTokenFromHeader
from pydantic import BaseModel
from src.Roadmap.Recommend import aiRecommendRoadmapFromToken, getRoadmapOptions, getSvgUrlByName, askAiForRoadmaps,getUserTagsTest
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
app = FastAPI(title="Roadmap Service API")

class RecommendRequest(BaseModel):
    userId: int


def ClearAndSaveData():
    try:
        # 1. 초기화
        print(f"[{datetime.datetime.now()}] 데이터 초기화 작업 시작")
        ClearRoadmap()  # DB 초기화
        ClearStorage()  # 스토리지 초기화

        # 2. 데이터 재등록
        df = GetRoadmapDf()  # 로드맵 데이터 가져오기
        for _, row in df.iterrows():
            data = {
                "roadmapType": row['roadmapType'],
                "roadmapName": row['roadmapName'],
                "roadmapUrl": row['urlName'],
                "svgUrl": None,
            }
            UploadRoadmap(data)  # DB에 데이터 저장
        print(f"[{datetime.datetime.now()}] 데이터 초기화 및 저장 완료")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] 데이터 초기화 작업 실패: {e}")
        traceback.print_exc()
        raise Exception(f"초기화 작업 실패: {e}")

@app.post("/api/scheduler/initialize")
def initialize_data():
    """
    API를 통해 데이터 초기화 및 저장 작업을 수동으로 실행.
    """
    try:
        ClearAndSaveData()
        return {
            "status": "200",
            "message": "데이터 초기화 및 저장 작업이 완료되었습니다.",
            "data": None
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "500",
                "message": f"초기화 작업 실패: {str(e)}"
            }
        )



# 로드맵 재로드를 하는 스케줄러 실행
def scheduled_job():
    print(f"[{datetime.datetime.now()}] [스케줄러] 로드맵 재로드 실행")
    global df
    df = GetRoadmapDf()
    try:
        SaveRoadmaps()
        loop = asyncio.get_event_loop()
        loop.create_task(SaveRoadmapImage())
        print("[스케줄러] DB 및 SVG 저장 완료")
    except Exception as e:
        print(f"[스케줄러 오류] {e}")


# 스케줄러 시작 함수
def start_scheduler(cron_time: str):
    """매일 새벽 3시 정각에 작업 실행 (서버 시간 기준)"""
    if scheduler.running:
        print("[스케줄러] 이미 실행 중입니다.")
        return

    hour, minute = map(int, cron_time.split(" "))
    trigger = CronTrigger(hour=hour, minute=minute)
    scheduler.add_job(ClearAndSaveData, trigger)
    scheduler.start()
    print(f"[스케줄러] 매일 {hour:02d}:{minute:02d}에 데이터 초기화 작업이 실행됩니다.")

# 스케줄러 시작 (서버 시작 시)
@app.on_event("startup")
async def app_startup():
    print("[시작] 스케줄러 시작")
    cron_time = os.getenv("CRON_TIME", "3 0")  # 기본값: 매일 오전 3시
    start_scheduler(cron_time)

# 스케줄러 종료 (서버 종료 시)
@app.on_event("shutdown")
async def app_shutdown():
    print("[종료] 스케줄러 종료")
    scheduler.shutdown()



# CORS 설정 (필요시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
                "message": "로드맵 리스트를 성공적으로 불러왔습니다.",
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

# 로드맵을 크롤링해서 svg 형태로 Supabase에 저장
@app.post("/api/roadmap/saveImage")
async def SaveRoadmapImage():
    """SVG 파일을 roadmap.sh에서 크롤링하고 Supabase에 저장"""
    records = ReadRoadmapAllList()
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
    try:
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
                await browser.close()
                continue

            try:
                page = await browser.newPage()
                await page.setViewport({'width': 1980, 'height': 1080})
                await page.goto(url, {'waitUntil': 'load', 'timeout': 180000})

                # SVG 요소 검색
                svgElement = None
                for _ in range(30):
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
                    await browser.close()
                    continue

                # SVG 추출 및 저장
                svgHtml = await page.evaluate('(element) => element.outerHTML', svgElement)
                # SVG 파일 로컬 저장
                fileName = f"{roadmapName}Roadmap.svg"
                localPath = f"/tmp/{fileName}"
                with open(localPath, 'w', encoding='utf-8') as f:
                    f.write(svgHtml)

                # Supabase 스토리지에 png 업로드
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
                results.append({
                    "roadmapName": roadmapName,
                    "status": f"에러 발생: {e}",
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

# supabase에 저장되어 있는 로드맵 svg파일의 url을 보여주기 위해
@app.get("/api/roadmap/view")
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

            return {
                "status": "200",
                "message": "SVG URL 조회 성공",
                "data": svgUrl
            }


        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "500",
                    "message": f"로드맵 SVG URL 조회 실패: {e}",
                    "data": None
                }
            )

# supabase에 저장되어 있는 로드맵 svg파일를 개인별로 추천해서 보여줌
@app.post("/api/roadmap/ai-recommend")
async def aiRecommendRoadmaps(req: Request):
    return await aiRecommendRoadmapFromToken(req)

@app.post("/api/roadmap/ai-recommend-test")
async def aiRecommendRoadmapsTest(req: RecommendRequest):
    """
    테스트용: userId를 받아서 추천 로드맵을 반환
    """
    try:
        roadmapOptions = getRoadmapOptions()
        tags = await getUserTagsTest(req.userId)
        selectedNums = askAiForRoadmaps(tags, roadmapOptions)

        recommendedRoadmaps = []
        for num in selectedNums:
            if num in roadmapOptions:
                roadmapName = roadmapOptions[num]["roadmapName"]
                svgUrl = getSvgUrlByName(roadmapName)
                recommendedRoadmaps.append({
                    "roadmapName": roadmapName,
                    "svgUrl": svgUrl
                })
        return {
            "userTags": tags,
            "aiSelectedNumbers": selectedNums,
            "recommendedRoadmaps": recommendedRoadmaps}
    except HTTPException as e:
        raise HTTPException(status_code=500, detail=f"추천 실패: {str(e)}")


# 태그 + 깃허브 요청하는코드(api top_k)
# Alice cloude에 태그와 깃허브, 로드맵 리스트를 보내서 가장 잘 어울리는 로드맵 추천

##### 로드맵 이름이랑 url을 받으면 rdb supabseUrl을 다시 던져주기