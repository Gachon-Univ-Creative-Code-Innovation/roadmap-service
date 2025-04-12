from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from crawlingToText import get_roadmap_df
from pyppeteer import launch
import asyncio

app = FastAPI()
df = get_roadmap_df()

@app.get("/")
async def root():
    return {"message": "Roadmap API is running"}

@app.get("/favicon.ico")
def favicon():
    return {"message": "No favicon"}


@app.get("/roadmaps")
def read_all_roadmaps():
    """전체 로드맵 리스트 반환"""
    return df.to_dict('records')

@app.get("/roadmaps/{url_name")
async def get_roadmap_svg(url_name: str):
    """SVG 파일을 실시간으로 생성하여 응답"""
    roadmap_df = df[df['urlName'] == url_name]
    if roadmap_df.empty:
        raise HTTPException(status_code=404, detail = f"로드맵을 찾을 수 없습니다: https://roadmap.sh/{url_name}")

    roadmap_url = roadmap_df.iloc[0]['roadmapName']
    url = f"https://roadmap.sh/{url_name}"

    try:
        browser = await launch(headless = True)
        page = await browser.newPage()
        await page.setViewport({'width': 1980, 'height':1080})
        await page.goto(url, {'waitUntil': 'load', 'timeout':180000})

        svg_element = None
        for _ in range(60):
            svg_element = await page.querySelector('#resource-svg-wrap svg')
            if svg_element:
                break
            await asyncio.sleep(1)

        if not svg_element:
            await browser.close()
            raise HTTPException (status_code=404, detail= f"SVG요소를 찾을 수 없습니다.")

        svg_html = await page.evaluate('(element) => element.outerHTML', svg_element)
        await browser.close()
        return Response(content = svg_html, media_type = "image/svg+xml")

    except Exception as e:
        raise HTTPException( status_code =500, detail=f"SVG 추출 실패: {e}")

@app.post("/roadmaps/save/{url_name")
async def save_roadmap_svg(url_name: str):
    """SVG파일 저장"""
    roadmap_df = df[df['urlName'] ==url_name]
    if roadmap_df.empty:
        raise HTTPException( status_code = 404, detail = f"로드맵을 찾을 수 업습니다: https://roadmap.sh/{url_name}")

    roadmap_name = roadmap_df.iloc[0]['roadmapName']
    url = f"https://roadmap.sh/{url_name}"

    try:
        browser = await launch(headless=True)
        page = await browser.newPage()
        await page.setViewport({'width': 1980, 'height': 1080})
        await page.goto(url, {'waitUntil': 'load', 'timeout': 180000})

        svg_element = None
        for _ in range(60):
            svg_element = await page.querySelector('#resource-svg-wrap svg')
            if svg_element:
                break
            await asyncio.sleep(1)

        if not svg_element:
            await browser.close()
            raise HTTPException(status_code=404, detail="SVG 요소를 찾을 수 없습니다.")

        svg_html = await page.evaluate('(element) => element.outerHTML', svg_element)
        file_name = f"{roadmap_name}_roadmap.svg"
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(svg_html)

        await browser.close()
        return {'message': f'Saved as {file_name}'}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"저장 실패 실패: {e}")
