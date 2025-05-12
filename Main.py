from fastapi import FastAPI, HTTPException,UploadFile, Form, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from src.Crawling.CrawlingToText import GetRoadmapDf
from src.Utils.RepoToDB import UploadRoadmap
from src.Utils.RepoToStorage import UploadSvgToStorage
from pyppeteer import launch
import asyncio
import shutil
import os

app = FastAPI(title="Roadmap Service API")
df = GetRoadmapDf()

# CORS 설정 (필요시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# health check
@app.get("/api/roadmap/health-check")
async def healthCcheck():
    return {"status":200, "message": "서버 상태 확인", "data" :"working"}

# favicon 요청 무시
@app.get("/api/roadmap/favicon.ico")
def favicon():
    return {"status" : 400, "message": "No favicon"}


@app.get("/api/roadmap")
def ReadAllRoadmaps():
    """전체 로드맵 리스트 반환"""
    return df.to_dict('records')

@app.get("/api/roadmap/{urlName}")
async def GetRoadmapSvg(urlName: str):
    """SVG 파일을 실시간으로 생성하여 응답"""
    roadmapDf = df[df['urlName'] == urlName]
    if roadmapDf.empty:
        raise HTTPException(status_code=404, detail = f"로드맵을 찾을 수 없습니다: https://roadmap.sh/{urlName}")

    # roadmapUrl = roadmapDf.iloc[0]['roadmapName']
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
            raise HTTPException (status_code=404, detail= f"SVG요소를 찾을 수 없습니다.")

        svgHtml = await page.evaluate('(element) => element.outerHTML', svgElement)
        await browser.close()
        return Response(content = svgHtml, media_type = "image/svg+xml")

    except Exception as e:
        raise HTTPException( status_code =500, detail=f"SVG 추출 실패: {e}")

@app.post("/api/roadmap/save/{url_name}")
async def SaveRoadmapSvg(urlName: str):
    """SVG파일을 roadmap.sh에서 크롤링하고 Supabase에 저장"""
    # 로드맵 이름 조회
    roadmapDf = df[df['urlName'] ==urlName]
    if roadmapDf.empty:
        raise HTTPException( status_code = 404, detail = f"로드맵을 찾을 수 업습니다: https://roadmap.sh/{urlName}")

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
            raise HTTPException(status_code=404, detail="SVG 요소를 찾을 수 없습니다.")

        svgHtml = await page.evaluate('(element) => element.outerHTML', svgElement)
        # SVG 파일 로컬 저장
        fileName = f"{roadmapName}Roadmap.svg"
        localPath = f"/tmp/{fileName}"
        with open(fileName, 'w', encoding='utf-8') as f:
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
            "message": f"로드맵 SVG가 Supabase에 저장되었습니다: {fileName}."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"저장 실패 실패: {e}")
