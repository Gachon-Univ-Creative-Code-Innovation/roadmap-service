from DBClient import DBClientCall

from DBClient import DBClientCall

supabase = DBClientCall()

def UploadRoadmap(data: dict):
    result = supabase.table("roadmaps").insert(data).execute()
    return result
