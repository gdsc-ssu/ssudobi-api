import asyncio
import datetime as dt

from datetime import datetime
from functools import partial

from aiohttp_retry import RetryClient
from login_session import *

from dataclasses import dataclass, field

HOLIDAY = 5

SEMINA_ROOMS = (1, 2, 3, 4, 5, 6, 7, 9)
OPEN_SEMINA_ROOMS = (18, 21, 22, 23, 24, 25, 26)


@dataclass
class DateReservation:
    def init_data(self):
        if self.room_type == 1:
            return SEMINA_ROOMS
        elif self.room_type == 5:
            return OPEN_SEMINA_ROOMS
        else:
            raise ValueError(
                "Room type id is wrong 1 for semina room 5 for open semina room"
            )

    room_type: int
    date: str
    data: dict[int, list[tuple]] = field(default_factory=dict)

    def __post_init__(self):  # 값 초기화
        self.data = {x: [] for x in self.init_data()}


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
        json_data = await resp.json(content_type=None)  # 응답 바이트를 읽음

    return json_data


def parse_resravtion_status(room_type: int, res: dict) -> DateReservation:
    """
    json 데이터를 파싱해 시간대 별 예약 가능 여부를 갖고 있는 불리언 딕셔너리를 생성합니다.

    Args:
        time_table (dict): 예약 가능 시간 테이블
        res (requests.Response): 예약 조회 api 응답 결과

    Returns:
        dict: True인 경우 해당 시간대에 예약 가능을 의미하고 False인 경우 예약 불가능을 의미합니다.
            ex) {10: True, 11: True, 12: True, 13: True, 14: True, 15: True, 16: True, 17: True, 18: True}

    """

    code = res.get("code", "")  # 도서관 api의 자체 응답 코드

    if res.get("success") == False:  # 요청이 실패한 경우
        raise ValueError(code)

    if code == "success.retrieved":  # 예약이 존재하는 경우
        room_reservations = res["data"]["list"]
        hope_date = room_reservations[0]["hopeDate"]  # 조회일자
        date_reservation = DateReservation(room_type=1, date=hope_date)

        for room in room_reservations:
            room_id: int = room["id"]
            room_time_lines = room["timeLine"]
            begin_hour: int = room_time_lines[0]["hour"]

            for time_line in room_time_lines:
                minutes: list[dict] = time_line["minutes"]
                hour = time_line["hour"]
                is_reserved = (
                    True
                    if minutes[0]["class"]
                    else False  # 첫번째 시간대만 파악하면 예약 여부를 확인 할 수 있다.
                )  # 예약 여부 확인

                if is_reserved:  # 현재 예약이 이미 차있는 경우
                    if hour - begin_hour > 1:
                        date_reservation.data[room_id].append((begin_hour, hour))
                        begin_hour = hour

    return date_reservation


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
        reservation_status: list | None = parse_resravtion_status(
            response
        )  # 예약 정보 추출
        return reservation_status

    except asyncio.CancelledError:
        print(
            f">> Canceled date:{date} room_number:{room_number}"
        )  # 실행중 에러가 발생한 경우


async def get_all_rooms_reservation_status(
    retry_client: RetryClient, room_type_id: int, date: str
) -> dict:
    """
    주어진 날짜에 해당하는 모든 세미나실의 예약 정보를 반환한다.

    Args:
        date (str): 조회할 날짜

    Returns:
        list[dict]:하루 동안 모든 세미나실의 예약 현황 리스트
    """
    reservations_in_day = {}  # 하루동안의 총 예약

    def update_res(task: asyncio.Task, room_number: int):
        reservations_in_day[room_number] = task.result()  # task의 실행 결과를 기록한다

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
    available_day_count = 0  # 사용 가능 일수
    day_diff = iter(range(30))  # 최대 일자 탐색 범위
    result = {}
    while available_day_count < MAX_RESERVATION_DAY:  # 사용 가능일이 14일을 넘으면 종료
        current_date = now_date + dt.timedelta(days=next(day_diff))  # 하루 씩 이동
        day = current_date.weekday()  # 요일 추출
        if (
            day > HOLIDAY
        ):  #  토:5  일:6 방학에는 주말 양일 이용이 불가하고 학기 중에는 일요일만 예약이 불가하다.
            continue

        current_date_str = current_date.strftime("%Y-%m-%d")
        all_reservation_status = await get_all_rooms_reservation_status(
            retry_client, current_date_str  # 오늘 날짜
        )  # 모든 예약 현황

        result[current_date_str] = all_reservation_status
        available_day_count += 1

    return result


async def get_cache_data(token: str):
    # date = "2023-08-28"  # 조회 날짜
    # room_number = 1
    session = await get_logined_session(token)
    retry_client = await create_retry_client(session)

    async with retry_client:
        res = await get_reservation_status(retry_client, date, room_number)
        # res = await get_all_rooms_reservation_status(retry_client, date)
        # res = await get_all_days_reservation_status(retry_client)
    return res


if __name__ == "__main__":
    token = "uf4asg5stjdt1das3h54m0ivo9kmulv3"
    asyncio.run(get_cache_data(token))
