import asyncio
import json

import boto3
import json

from caching import get_cache_data
from login_session import *


async def update_cache(student_id: str, password: str) -> dict:
    """
    캐싱 로직을 전부 실행해 현재 예약 현황을 반환 합니다.

    Args:
        student_number (str): 학번
        student_name (str): 이름

    Returns:
        dict:
    """
    session = await get_logined_session(student_id, password)  # 로그인 세션 생성
    retry_client = await create_retry_client(session)  # 세션에 retry 기능 추가
    cache_data = await get_cache_data(retry_client)  # 예약 현황 추출
    await retry_client.close()

    return cache_data


def put_cache_s3(cache: dict):
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket="ssudobi-cache", Key="cache", Body=json.dumps(cache)
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
        body = json.loads(event["body"])
        student_id = body["student_id"]
        password = body["password"]
        res = asyncio.run(update_cache(student_id, password))  # 예약 현황 조회
        # put_cache_s3(res)
        response = create_response(200, json.dumps({"data": res}))

    except AssertionError as e:
        response = create_response(401, json.dumps({"data": str(e)}))

    except Exception as e:
        response = create_response(500, json.dumps({"data": str(e)}))

    finally:
        return response
