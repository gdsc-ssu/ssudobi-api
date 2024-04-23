import asyncio
import pytest
import requests
import time

from api import create_logined_session
from case import CASEDICT, SUCCESSICT
from caching import get_date_reservations, parse_resravtions
from env import *
from logger_ import logger


ERROR_CODES = (401, 500)


class TestParser:
    async def run(self, room_type_id: int, date: str):
        session = await create_logined_session(STUDENT_ID, USAINT_SECRET, [])
        res = await get_date_reservations(session, room_type_id, date)
        return res

    @pytest.mark.parametrize(
        "room_type_id, date",
        [
            (1, "2024-04-26"),
            (5, "2024-04-26"),
            (1, "2024-04-27"),
            (5, "2024-04-27"),
            (1, "2024-04-29"),
            (5, "2024-04-29"),
        ],
    )  # (룸 타입, 날짜)
    def test_parse(self, room_type_id: int, date: str):
        response: dict = CASEDICT[date][room_type_id]
        success_case: dict = SUCCESSICT[date][room_type_id]
        res = parse_resravtions(room_type_id, date, response)
        parsed_data = res.data
        assert parsed_data == success_case, "Result mismatched!"


class TestDocker:
    # URL 및 데이터 설정
    base_url = "http://localhost:9000/2015-03-31/functions/function/invocations"
    post_data = {"pathParameters": {"room_type_id": "1"}}

    # POST 요청을 테스트하는 기능
    def send_post_request(self, url, data):
        response = requests.post(url, json=data)
        return response

    # 각 시간 단위에 대한 테스트
    @pytest.mark.parametrize(
        "duration, interval", [(1, 5), (5, 5), (10, 5)]
    )  # (분, 초)
    def test_periodic_requests(self, duration, interval):
        total_duration = duration * 60  # 분을 초로 변환
        end_time = time.time() + total_duration
        error_cnt = 0
        while time.time() < end_time:
            try:
                response = self.send_post_request(self.base_url, self.post_data)
                status_code = response.json()["statusCode"]
                assert status_code not in ERROR_CODES, "Bad Reqeust"

                logger.info(f"Success: {response.text}")
                time.sleep(interval)

            except Exception as e:
                logger.error(f"Error occurs during test: {e}")
                error_cnt += 1

        assert error_cnt == 0, "ERROR OCCURED!"
