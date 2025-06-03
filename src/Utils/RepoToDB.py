import os
import requests
from dotenv import load_dotenv
from src.Utils.DBClient import DBClientCall

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = DBClientCall()

def UploadRoadmap(data: dict):
    try:
        # 새로운 데이터 삽입
        result = supabase.table("Roadmap_DB").insert(data).execute()
        print(f"[삽입 완료] roadmapName: {data.get('roadmapName')}")
        return result
    except Exception as e:
        print(f"[삽입 실패] {e}")
        raise

def ClearRoadmap():
    try:
        url = f"{SUPABASE_URL}/rest/v1/rpc/clear_roadmap_db"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers)

        if response.status_code in [200, 204]:
            print("[DB 초기화 완료] Roadmap_DB가 초기화되고 rodamapID가 재설정되었습니다.")
        else:
            print(f"[DB 삭제 실패] {response.status_code}: {response.text}")
            raise Exception(response.text)
    except Exception as e:
        print(f"[RPC 요청 실패] {e}")
        raise

def ReadRoadmapList():
    result = supabase.table("Roadmap_DB").select("*").execute()
    return result.data

def UpdateRoadmap(roadmapName: str, svgUrl: str):
    result = supabase.table("Roadmap_DB") \
        .update({"svgUrl": svgUrl}) \
        .eq("roadmapName", roadmapName) \
        .execute()
    return result
