import asyncio
import json
import traceback

import boto3
import json

from env import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION_NAME, CACHE_BUCKET
from api import refresh_login_session
from caching import get_all_date_reservations


tokens = []


async def update_cache(room_type_id: int) -> list[dict] | None:
    """
    람다를 따뜻하게 유지해 세션을 최대한 재활용 합니다.
    세션이 만료된 경우에만 로그인을 재시도 합니다.
    이후 해당 세션을 활용해 캐싱 로직을 수행합니다.

    Args:
        room_type_id (str): 방 번호

    Returns:
        dict:
    """

    session = await refresh_login_session(tokens)

    if session is None:
        raise AssertionError("Login Failed")

    async with session:
        try:
            cache_data: list[dict] = await get_all_date_reservations(
                session, room_type_id
            )  # 예약 현황 추출
            return cache_data

        except Exception:  # 요청이나 응답에 문제가 발생하는 경우
            print(traceback.format_exc())


def put_cache_s3(cache: dict):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION_NAME,
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


def handler(event: dict, context: dict) -> dict:
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
        room_type_id = event["pathParameters"].get("room_type_id", "1")
        room_type_id = int(room_type_id)
        res = asyncio.run(update_cache(room_type_id))  # 예약 현황 조회
        if res:
            put_cache_s3({"reservation": res})
        response = create_response(200, json.dumps(res))

        global tokens
        tokens[0] = "ofvmjhurg9afr8j2sh5lsb035u0kdms8"

    except AssertionError as e:
        response = create_response(401, json.dumps({"data": str(e), "log": str(e)}))

    except Exception as e:
        response = create_response(500, json.dumps({"data": str(e), "log": str(e)}))

    finally:
        return response
