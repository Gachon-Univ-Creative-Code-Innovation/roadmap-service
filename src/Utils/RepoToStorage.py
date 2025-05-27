from DBClient import DBClientCall, BucketCall

def UploadSvgToStorage(filename: str, local_path: str):
    supabase = DBClientCall()
    bucket = BucketCall()
    bucket.upload(local_path, path=filename)
    return True