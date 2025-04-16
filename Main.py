from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from src.CrawlingToText import GetRoadmapDf
from pyppeteer import launch
import asyncio

app = FastAPI(title="Roadmap Service API")
df = GetRoadmapDf()

# health check
@app.get("/api/roadmap/health-check")
async def healthCcheck():
    return {"status":200, "message": "서버 상태 확인", "data" :"working"}

@app.get("/api/roadmap/favicon.ico")
def favicon():
    return {"status" : 400, "message": "No favicon"}


@app.get("/api/roadmap")
def ReadAllRoadmaps():
    """전체 로드맵 리스트 반환"""
    return df.to_dict('records')

@app.get("/api/roadmap/{urlName")
async def GetRoadmapSvg(urlName: str):
    """SVG 파일을 실시간으로 생성하여 응답"""
    roadmapDf = df[df['urlName'] == urlName]
    if roadmapDf.empty:
        raise HTTPException(status_code=404, detail = f"로드맵을 찾을 수 없습니다: https://roadmap.sh/{urlName}")

    roadmapUrl = roadmapDf.iloc[0]['roadmapName']
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
    """SVG파일 저장"""
    roadmapDf = df[df['urlName'] ==urlName]
    if roadmapDf.empty:
        raise HTTPException( status_code = 404, detail = f"로드맵을 찾을 수 업습니다: https://roadmap.sh/{urlName}")

    roadmapName = roadmapDf.iloc[0]['roadmapName']
    url = f"https://roadmap.sh/{urlName}"

    try:
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
        fileName = f"{roadmapName}_roadmap.svg"
        with open(fileName, 'w', encoding='utf-8') as f:
            f.write(svgHtml)

        await browser.close()
        return {"status":"200", "message": f"Saved as {fileName}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"저장 실패 실패: {e}")
