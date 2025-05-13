import os
from dotenv import load_dotenv
from supabase import create_client

# DB에 접근하는 Key 부르는 함수
def DBClientCall():
    envPath = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    load_dotenv(dotenv_path=os.path.abspath(envPath))

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    # DB 접근 Client 생성
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    return supabase


# DB Bucket 이름 불러오는 함수
def BucketCall():
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")

    return SUPABASE_BUCKET
