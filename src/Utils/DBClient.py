import os
from dotenv import load_dotenv
from supabase import create_client, Client

envPath = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(envPath))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")

# DB 접근 Client 생성
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# DB에 접근하는 Key 부르는 함수
def DBClientCall():
    return supabase


# DB Bucket 이름 불러오는 함수
def BucketCall():
    return supabase.storage.from_(SUPABASE_BUCKET)
