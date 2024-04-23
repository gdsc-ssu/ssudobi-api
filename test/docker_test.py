import logging
import pytest
import requests
import time


logger = logging.getLogger("TestLogger")
logger.setLevel(logging.DEBUG)  # DEBUG 레벨 이상의 모든 이벤트 기록

# 로그 핸들러 설정
error_handler = logging.FileHandler("log/errors.log")  # 실패한 테스트 로그 파일
error_handler.setLevel(logging.ERROR)  # ERROR 이상 로그 기록
success_handler = logging.FileHandler("log/success.log")  # 성공한 테스트 로그 파일
success_handler.setLevel(logging.INFO)  # INFO 이상 로그 기록

# 로그 형식 설정
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
error_handler.setFormatter(formatter)
success_handler.setFormatter(formatter)

# 로거에 핸들러 추가
logger.addHandler(error_handler)
logger.addHandler(success_handler)


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
        "duration, interval", [(1, 5), (5, 5), (60, 5)]
    )  # (분, 초)
    def test_periodic_requests(self, duration, interval):
        total_duration = duration * 60  # 분을 초로 변환
        end_time = time.time() + total_duration

        errors = {code: 0 for code in [401, 500]}

        while time.time() < end_time:
            try:
                response = self.send_post_request(self.base_url, self.post_data)
                response.raise_for_status()
                logger.info(f"Success: {response.text}")
                time.sleep(interval)

            except Exception as e:
                logger.error(f"Error occurs during test: {e}")
                status_code = response.status_code
                if status_code in errors:
                    errors[status_code] += 1

        if sum(errors.values()):
            for code, count in errors.items():
                logger.error(f"code:{code} count:{count}")
