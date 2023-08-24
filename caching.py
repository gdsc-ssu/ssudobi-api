import asyncio
import datetime as dt
import json

from datetime import datetime
from functools import partial

from aiohttp_retry import RetryClient


async def call_api(retry_client: RetryClient, date: str, room_number: int) -> dict:
    """
    특정 날짜의 특정 세미나실의 예약현황을 조회 api를 호출해 결과를 반환한다.

    Args:
        date (str): 조회할 날짜 2023-08-20
        room_number (int): 룸 번호(1 ~ 8) 개방형 (18, 21 ~ 26)
    Return:
        dict: 예약 현황 응답 객체
    """
    status_url = f"https://oasis.ssu.ac.kr/smufu-api/api/pc/rooms/{room_number}/reservations?date={date}"
    async with retry_client.get(status_url) as resp:
        resp_bytes = await resp.read()  # 응답 바이트를 읽음
        json_data = json.loads(resp_bytes)  # 바이트를 json으로 변환

    return json_data


def parse_resravtion_status(res: dict) -> list | None:
    """
    json 데이터를 파싱해 시간대 별 예약 가능 여부를 갖고 있는 불리언 딕셔너리를 생성합니다.

    Args:
        time_table (dict): 예약 가능 시간 테이블
        res (requests.Response): 예약 조회 api 응답 결과

    Returns:
        dict: True인 경우 해당 시간대에 예약 가능을 의미하고 False인 경우 예약 불가능을 의미합니다.
            ex) {10: True, 11: True, 12: True, 13: True, 14: True, 15: True, 16: True, 17: True, 18: True}

    """
    str_to_datetime = lambda x: datetime.strptime(
        x, "%Y-%m-%d %H:%M:%S"
    )  # str -> datetime으로
    code = res.get("code", "")  # 도서관 api의 자체 응답 코드

    if res.get("success") == False:  # 요청이 실패한 경우
        raise ValueError(code)

    if code == "success.retrieved":  # 예약이 존재하는 경우
        reservation_list = res["data"]["list"]
        reserved_times = []

        now = datetime.now()  # 현재 시간
        for rsv in reservation_list:
            begin_time = str_to_datetime(rsv["beginTime"])  # 예약 시작시간
            end_time = str_to_datetime(rsv["endTime"])  # 예약 종료시간

            start_hour = (
                begin_time.hour if begin_time >= now else now.hour
            )  # 예약일이 오늘일 경우 현재 시간을 기준으로 한다

            reserved_times.append((start_hour, end_time.hour))  # 예약이 차있는 시간대 추출
        return reserved_times


async def get_reservation_status(
    retry_client: RetryClient, date: str, room_number: int
) -> list | None:
    """
    해당일의 세미나실 예약 현황을 반환한다

    Args:
        sess (RetryClient): 세션
        date (str): 날짜
        room_number (int): 방 번호

    Returns:
        dict: 예약현황
    """
    try:
        response: dict = await call_api(retry_client, date, room_number)  # api 호출 값
        reservation_status = parse_resravtion_status(response)  # 예약 정보 추출
        return reservation_status

    except asyncio.CancelledError:
        print(f">> Canceled date:{date} room_number:{room_number}")


async def get_all_rooms_reservation_status(
    retry_client: RetryClient, date: str
) -> dict:
    """
    주어진 날짜에 해당하는 모든 세미나실의 예약 정보를 반환한다.

    Args:
        date (str): 조회할 날짜

    Returns:
        list[dict]:하루 동안 모든 세미나실의 예약 현황 리스트
    """
    semina_room_numbers = [1, 2, 3, 4, 5, 6, 7, 9]
    opend_room_numbers = [18, 21, 22, 23, 24, 25, 26]
    all_room_numbers = semina_room_numbers + opend_room_numbers
    reservations_in_day = {i: None for i in all_room_numbers}  # 하루동안의 총 예약

    def update_res(task: asyncio.Task, room_number: int):
        reservations_in_day[room_number] = task.result()  # task의 실행 결과를 기록한다

    tasks = []  # 비동기로 처리할 테스크 집합
    for i in all_room_numbers:
        task = asyncio.create_task(
            get_reservation_status(retry_client, date, i)
        )  # task 생성
        call_back = partial(update_res, room_number=i)  # 결과 기록을 위한 call back
        task.add_done_callback(call_back)  # 콜백 등록
        tasks.append(task)

    await asyncio.gather(*tasks, return_exceptions=False)  # 등록된 테스크 비동기 실행
    return reservations_in_day


async def get_all_days_reservation_status(retry_client: RetryClient) -> dict:
    """
    모든 날짜와 모든 세미나 실의 예약 현황을 조회해 현재의 예약 현황을 반환 합니다.
    예약 조회는 예약 가능일 기준 14일을 조회하며 이후는 조회를 하여도 예약이 불가하기 때문에 조회하지 않습니다.
    사용 가능일은 기준으로 하기 때문에 주말과 공휴일은 포함되지 않습니다.
    #TODO 공휴일 지원안됨

    Args:
        retry_client (RetryClient): 세션 객체

    Returns:
        dict: 모든 날짜 모든 세미나 실의 예약 현황 객체를 반환 합니다.
    """
    now_date = datetime.today()
    MAX_RESERVATION_DAY = 14  # 최대 예약 가능 시점은 현재부터 14일 뒤까지
    day_count = 0  # 사용 가능 일수
    result = {}
    for delta in range(30):  # 한달을 조회하면 사용 가능일 수 14일은 필연적으로 채운다 (무한루프 대용)
        current_date = now_date + dt.timedelta(days=delta)

        day = current_date.weekday()  # 요일 추출
        if day >= 5:  # 주말인 경우 예약 불가함으로 패스한다 토:5  일:6
            continue

        current_date_str = current_date.strftime("%Y-%m-%d")

        all_reservation_status = await get_all_rooms_reservation_status(
            retry_client, current_date_str  # 오늘 날짜
        )  # 모든 예약 현황

        result[current_date_str] = all_reservation_status

        if (day_count := day_count + 1) == MAX_RESERVATION_DAY:  # 사용 가능일이 14일을 넘으면 종료
            break

    return result


async def get_cache_data(retry_client: RetryClient):
    date = "2023-08-28"  # 조회 날짜
    # room_number = 1
    async with retry_client:
        # res = await get_reservation_status(retry_client, date, room_number)
        # res = await get_all_rooms_reservation_status(retry_client, date)
        res = await get_all_days_reservation_status(retry_client)
    return res


# if __name__ == "__main__":
# asyncio.run(get_cache_data())
