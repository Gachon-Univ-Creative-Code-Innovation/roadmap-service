from src.Utils.DBClient import BucketCall
from storage3.utils import StorageException

bucket = BucketCall()

def ClearStorage():
    try:
        # 버킷 내 모든 파일 목록 가져오기
        file_list = bucket.list()
        if not file_list:
            print("[Storage 초기화] 삭제할 파일 없음")
            return

        # 파일 이름만 추출하여 삭제
        filenames = [file['name'] for file in file_list]
        bucket.remove(filenames)
        print(f"[Storage 초기화 완료] 총 {len(filenames)}개의 파일 삭제됨")
    except StorageException as e:
        print(f"[Storage 삭제 실패] {e}")
        raise

def UploadStorage(filename: str, local_path: str):
    # 파일이 이미 존재하면 삭제
    try:
        with open(local_path, "rb") as f:
            bucket.upload(path=filename, file=f)
            print(f"[업로드 완료] {filename}")
    except StorageException as e:
        print(f"[업로드 실패] {filename} | {e}")
        raise

