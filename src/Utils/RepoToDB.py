from src.Utils.DBClient import DBClientCall

supabase = DBClientCall()


def UploadRoadmap(data: dict):
    try:
        result = supabase.table("roadmaps").insert(data).execute()
        return result
    except Exception as e:
        print("Error uploading roadmap:", e)
        return None
