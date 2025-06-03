from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx, requests, os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
VLLM_URL = os.getenv("VLLM_SERVER_URL")
MATCHING_URL = os.getenv("MATCHING_URL")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 요청 모델
class RecommendRequest(BaseModel):
    userId: int

# 1. 로드맵 DB에서 ID/Name 추출
def getRoadmapOptions():
    response = supabase.table("Roadmap_DB").select("roadmapId, roadmapName").execute()
    data = response.data
    numbered = {
        str(i + 1): {"roadmapId": row["roadmapId"], "roadmapName": row["roadmapName"]}
        for i, row in enumerate(data)
    }
    return numbered

# 2. 매칭 API에서 유저 태그 받아오기 (현재 더미 태그로 대체)
async def getUserTags(userId: int, topK: int = 5):
    # 실제 호출 시 주석 해제
    # async with httpx.AsyncClient() as client:
    #     response = await client.get(
    #         f"{MATCHING_URL}/api/matching-service/represent-tags",
    #         params={"userID": userId, "topK": topK}
    #     )
    #     response.raise_for_status()
    #     return response.json()["data"]

    # 실험용 더미 데이터
    return ["react", "typescript", "html"]

# 3. AI에게 로드맵 번호 추천 요청
def askAiForRoadmaps(tags: list[str], roadmapOptions: dict, topN: int = 3) -> list[str]:
    optionsText = "\n".join([f"{num}. {info['roadmapName']}" for num, info in roadmapOptions.items()])
    systemMsg = f"""다음은 추천할 수 있는 로드맵 목록입니다:
{optionsText}
사용자의 태그를 보고 가장 적합한 번호 {topN}개를 쉼표로 나열해서 출력하세요. 예: 1,3,7"""

    userMsg = f"태그: {tags}"

    response = requests.post(
        f"{VLLM_URL}",
        json={
            "model": "google/gemma-3-4b-it",
            "messages": [
                {"role": "system", "content": systemMsg},
                {"role": "user", "content": userMsg}
            ],
            "max_tokens": 20
        }
    )

    content = response.json()["choices"][0]["message"]["content"]
    print("AI 응답:", content)
    return [num.strip() for num in content.split(",") if num.strip().isdigit()]

# 4. 최종 FastAPI 엔드포인트
@app.post("/api/roadmap/ai-recommend")
async def aiRecommendRoadmaps(req: RecommendRequest):
    try:
        roadmapOptions = getRoadmapOptions()
        tags = await getUserTags(req.userId)
        selectedNums = askAiForRoadmaps(tags, roadmapOptions)

        recommended = [roadmapOptions[num] for num in selectedNums if num in roadmapOptions]

        return {
            "userTags": tags,
            "aiSelectedNumbers": selectedNums,
            "recommendedRoadmaps": recommended
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 실패: {str(e)}")

# 실행 방법 (CMD)
# uvicorn test5:app --reload

# 테스트 예시 (CMD)
# curl -X POST http://localhost:8000/api/roadmap/ai-recommend ^
#  -H "Content-Type: application/json" ^
#  -d "{\"userId\": 5}"

#수정할 내용, JWT 토큰에서 userID 가져오게 코드 수정하면 아래 코드 수정하면 됨.
# 요청 모델
#class RecommendRequest(BaseModel):
#    userId: int