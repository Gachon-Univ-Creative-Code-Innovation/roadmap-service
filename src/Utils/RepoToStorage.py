from src.Utils.DBClient import DBClientCall, BucketCall


def UploadSvgToStorage(filename: str, localPath: str):
    supabase = DBClientCall()
    bucket = BucketCall()

    _ = supabase.storage.from_(bucket).upload(
        filename, localPath, {"content-type": "text/markdown", "x-upsert": "true"}
    )

    return True
