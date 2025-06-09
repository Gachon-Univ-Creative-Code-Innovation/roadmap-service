import httpx
import time
import mimetypes
from src.Utils.DBClient import BucketCall
from storage3.utils import StorageException

bucket = BucketCall()

def ClearStorage():
    response = None
    try:
        # 버킷 내 모든 파일 목록 가져오기
        file_list = bucket.list()
        if not file_list:
            print("[Storage 초기화] 삭제할 파일 없음")
            return

        # 파일 이름만 추출하여 삭제
        filenames = [file['name'] for file in file_list]
        response = bucket.remove(filenames)
        print(f"[Storage 초기화 완료] 총 {len(filenames)}개의 파일 삭제됨")
    except StorageException as e:
        print(f"[Storage 삭제 실패] {e}")
        if response:
            print(f"서버 응답: {response}")
        raise Exception(f"[Storage 구성 실패]: {str(e)}")

    except httpx.RequestError as e:
        print(f"[Storage 삭제 실패 - 네트워크 오류] {e}")
        raise Exception(f"[네트워크 오류 발생]: {str(e)}")

    except Exception as e:
        print(f"[알 수 없는 오류]: {e}")
        raise Exception(f"[알 수 없는 오류 발생]: {str(e)}")


def UploadStorage(filename: str, local_path: str):
    response = None
    try:
        # 파일이 이미 존재하면 삭제
        with open(local_path, "rb") as f:
            try:
                bucket.remove([filename])
                print(f"[기존 파일 삭제 성공]: {filename}")
            except StorageException as e:
                print(f"[파일 삭제 실패 - 무시 가능] {filename} | {e}")
            except httpx.RequestError as e:
                print(f"[파일 삭제 실패 - 네트워크 오류] {filename} | {e}")

            try:
                response = bucket.upload(
                    path=filename,
                    file=f,
                )
                print(f"[업로드 완료] {filename} ")
                return response
            except (httpx.TimeoutException, httpx.ReadTimeout) as e:  # 타임아웃 예외 처리
                print(f"[업로드 실패 - 타임아웃 :{filename} | {str(e)}")
                raise Exception(f"[업로드 실패 - 타임아웃]: {filename}")
            except httpx.RequestError as e:
                print(f"[업로드 실패 - 네트워크 문제]: {filename} | {str(e)}")
                raise Exception(f"[업로드 실패 - 네트워크 오류]: {filename}")
    except Exception as e:
        print(f"[파일 처리 실패] {filename} | {e}")
        raise Exception(f"[파일 업로드 실패]: {filename}")