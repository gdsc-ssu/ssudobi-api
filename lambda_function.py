import asyncio
from contextlib import suppress
import json
import traceback

import boto3
import json

from env import *
from api import create_logined_session
from caching import get_all_date_reservations


token = ""


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
    global token

    for _ in range(3):
        session = await create_logined_session(STUDENT_ID, USAINT_SECRET, token)
        async with session:
            try:
                with suppress(TimeoutError):  # 타임아웃인 경우 그냥 다시 진행
                    cache_data: list[dict] = await get_all_date_reservations(
                        session, room_type_id
                    )  # 예약 현황 추출
                token = session._client.headers["pyxis-auth-token"]  # 기존 토큰 재활용
                return cache_data

            except AssertionError:  # 인증 오류가 발생한 경우
                token = None  # 토큰 리셋

            except Exception as e:  # 요청이나 응답에 문제가 발생하는 경우
                print(traceback.format_exc())
                raise e


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
        room_type_id = event.get("room_type_id", "1")
        room_type_id = int(room_type_id)
        res = asyncio.run(update_cache(room_type_id))  # 예약 현황 조회
        response = create_response(200, json.dumps(res))

    except AssertionError as e:
        response = create_response(
            401, json.dumps({"data": str(e), "log": str(traceback.format_exc())})
        )

    except Exception as e:
        response = create_response(
            500, json.dumps({"data": str(e), "log": str(traceback.format_exc())})
        )

    finally:
        return response


if __name__ == "__main__":
    res = asyncio.run(update_cache(1))  # 예약 현황 조회
    print(token)
    token = "ofvmjhurg9afr8j2sh5lsb035u0kdms8"
    res = asyncio.run(update_cache(1))  # 예약 현황 조회
    print(token)
