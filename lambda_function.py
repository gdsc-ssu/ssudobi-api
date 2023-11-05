import asyncio
import json

import boto3
import json

from caching import get_cache_data
from login_session import get_logined_session, create_retry_client


async def main(token: str) -> dict:
    """
    캐싱 로직을 전부 실행해 현재 예약 현황을 반환 합니다.

    Args:
        student_number (str): 학번
        student_name (str): 이름

    Returns:
        dict:
    """
    session = await get_logined_session(token)  # 로그인 및 세션 생성
    retry_client = await create_retry_client(session)  # 세션에 retry 기능 추가
    cache_data = await get_cache_data(retry_client)  # 예약 현황 추출
    return cache_data


def handler(event: dict, context: dict) -> dict | None:
    """
    캐싱 람다 함수를 호출 합니다.

    Args:
        event (dict, optional): api gateway에서 넘겨주는 event객체.
        context (dict, optional): api gateway에서 넘겨주는 컨텍스트 객체.

    Returns:
        dict: 람다 함수 실행 결과 값
    """
    response = None

    try:
        token = event.get("token")  # 로그인 토큰 조회
        if not token:
            raise AssertionError("Token is not passed")  # 토큰이 없는 경우

        res = asyncio.run(main(token))  # 예약 현황 조회
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket="ssudobi-cache", Key="cache", Body=json.dumps(res)
        )  # 캐시 업데이트
        response = {"StatusCode": 200, "data": res}

    except AssertionError as e:
        response = {"StatusCode": 422, "error": str(e)}  # 엔티티 에러

    except Exception as e:
        response = {"StatusCode": 500, "error": str(e)}  # 서버 자체 에러

    finally:
        return response
