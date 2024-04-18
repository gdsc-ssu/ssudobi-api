import asyncio
import json

import boto3
import json

from api import create_logined_session
from caching import get_all_date_reservations
from env import *

session = None


async def update_cache(room_type_id: int) -> dict | None:
    """
    캐싱 로직을 전부 실행해 현재 예약 현황을 반환 합니다.

    Args:
        student_number (str): 학번
        student_name (str): 이름

    Returns:
        dict:
    """

    for _ in range(3):  # 최대 3번 재시도

        global session
        if not session:
            session = await create_logined_session(
                STUDENT_ID, USAINT_SECRET
            )  # 로그인 세션 생성

        async with session:
            try:
                cache_data = await get_all_date_reservations(
                    session, room_type_id
                )  # 예약 현황 추출
                print(cache_data)
                return cache_data

            except (TypeError, ValueError):  # 요청이나 응답에 문제가 발생하는 경우
                session = None  # 세션 초기화를 위해사


def put_cache_s3(cache: dict):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION,
    )
    s3.put_object(
        Bucket=CACHE_BUCKET, Key="cache", Body=json.dumps(cache)
    )  # 캐시 업데이트


def create_response(status_code: str | int, msg: str) -> dict:
    response = {
        "isBase64Encoded": False,
        "headers": {"Content-Type": "application/json"},
        "statusCode": status_code,
        "body": msg,
    }
    return response


def handler(event: dict | None = None, context: dict | None = None) -> dict:
    """
    캐싱 람다 함수를 호출 합니다.

    Args:
        event (dict, optional): api gateway에서 넘겨주는 event객체.
        context (dict, optional): api gateway에서 넘겨주는 컨텍스트 객체.

    Returns:
        dict: 람다 함수 실행 결과 값
    """
    response = create_response(200, "empty")

    try:
        # room_type_id = event["pathParameters"]["room_type_id"]
        room_type_id = 1
        res = asyncio.run(update_cache(room_type_id))  # 예약 현황 조회
        if res:
            put_cache_s3(res)
        response = create_response(200, json.dumps({"data": res}))

    except AssertionError as e:
        response = create_response(401, json.dumps({"data": str(e)}))

    except Exception as e:
        response = create_response(500, json.dumps({"data": str(e)}))

    finally:
        return response


if __name__ == "__main__":
    res = handler()
    if res:
        put_cache_s3(res)
    print(res)
