import asyncio
from dataclasses import dataclass, field, asdict
import datetime

from aiohttp_retry import RetryClient

from api import create_logined_session, call_reservation_api


HOLIDAY = 5
SEMINA_ROOMS = (1, 2, 3, 4, 5, 6, 7, 9)
OPEN_SEMINA_ROOMS = (18, 21, 22, 23, 24, 25, 26)


@dataclass
class DateReservations:
    # 예약 정보 저장을 위한 클래스
    def init_room_number(self):
        if self.room_type_id == 1:
            return SEMINA_ROOMS
        elif self.room_type_id == 5:
            return OPEN_SEMINA_ROOMS
        else:
            raise ValueError(
                "Room type id is wrong 1 for semina room 5 for open semina room"
            )

    room_type_id: int
    date: str
    data: dict[int, list[tuple]] = field(default_factory=dict)
    is_open: bool = True

    def __post_init__(self):  # 값 초기화
        self.data = {
            x: [] for x in self.init_room_number()
        }  # 룸 타입에 맞게 방 번호 초기화


def parse_reserved_times(
    room_time_lines: list,
) -> list[tuple]:
    begin_hour = None  # 예약 시작 시간
    reserved_times = []
    for time_line in room_time_lines:
        minutes: list[dict] = time_line["minutes"]
        hour = time_line["hour"]
        is_reserved = (
            True
            if minutes[0]["class"]
            else False  # 첫번째 시간대만 파악하면 예약 여부를 확인 할 수 있다.
        )  # 예약 여부 확인

        if is_reserved:  # 현재 예약이 이미 차있는 경우
            if begin_hour is None:
                begin_hour = hour  # 예약 시작 시간

        elif begin_hour is not None:  # 0시인 경우도 존재
            reserved_times.append((begin_hour, hour))
            begin_hour = None

    if begin_hour and begin_hour != hour:  # 추가적으로 더 반영할 예약이 존재하는 경우
        reserved_times.append((begin_hour, hour))

    return reserved_times


def parse_resravtions(room_type_id: int, date: str, response: dict) -> DateReservations:
    """
    json 데이터를 파싱해 방 별로 예약이 존재하는 시간 들을 반환합니다.
    (10,13) => 10 ~ 13시까지 예약이 존재

    Args:
        room_type_id (int): 룸 타입
        response(dict): 예약 현황 정보

    """

    room_reservations: list = response["data"]["list"]  # 예약 정보
    date_reservations = DateReservations(room_type_id=room_type_id, date=date)
    hope_date = room_reservations[0].get("hopeDate")  # 예약 희망 일

    if hope_date:
        for room in room_reservations:
            is_chargeable: bool = room["isChargeable"]  # 예약 가능 여부
            if not is_chargeable:
                continue
            room_id: int = room["id"]
            room_time_lines: list = room["timeLine"]
            reserved_times: list[tuple] = parse_reserved_times(room_time_lines)
            date_reservations.data[room_id] = reserved_times
    else:
        date_reservations.is_open = False

    return date_reservations


async def get_date_reservations(
    session: RetryClient,
    room_type_id: int,
    date: str,
) -> DateReservations | None:
    """
    특정 세미나실의 1일간 예약 정보를 반환한다.

    Args:
        session (RetryClient): 세션
        room_type_id (int): 룸 타입 번호
        date (str): 일자

    Raises:
        ValueError: 리퀘스트가 잘못 요청된 경우
        TypeError: 리스폰스가 잘못 온 경우
        KeyError: 파싱이 잘못된 경우

    Returns:
        DateReservations | None: 예약 정보
    """
    try:
        response = await call_reservation_api(session, room_type_id, date)
        date_reservations = parse_resravtions(room_type_id, date, response)
        return date_reservations

    except AssertionError as e:
        raise AssertionError(
            f"Bad token in response date:{date} room_type:{room_type_id} {str(e)}"
        )

    except KeyError as e:
        raise KeyError(
            f"Bad key in parse response date:{date} room_type:{room_type_id} {str(e)}"
        )


def create_results(
    reservations: list[DateReservations | BaseException],
) -> list[dict]:
    """
    예약 정보에서 예외를 제거하고 필요한 결과만 반환한다.
    이후 날짜를 키로 하는 딕셔너리 형태의 데이터로 변환해 전송한다.

    Args:
        reservations (list[DateReservations  |  BaseException]): 예약 정보

    Returns:
        dict: 날짜 별 예약 데이터
    """
    results = []
    for reserv in reservations:
        if isinstance(reserv, DateReservations):
            results.append(asdict(reserv))
    return results


async def get_all_date_reservations(
    session: RetryClient, room_type_id: int
) -> list[dict]:
    """
    모든 날짜와 모든 세미나 실의 예약 현황을 조회해 현재의 예약 현황을 반환 합니다.
    예약 조회는 예약 가능일 기준 14일을 조회하며 이후는 조회를 하여도 예약이 불가하기 때문에 조회하지 않습니다.
    사용 가능일은 기준으로 하기 때문에 휴관일과 공휴일은 포함되지 않습니다.
    #TODO 공휴일 지원안됨

    Args:
        session (RetryClient): 세션 객체
        room_type_id (int): 룸 타입 번호


    Returns:
        dict: 모든 날짜 모든 세미나 실의 예약 현황 객체를 반환 합니다.
    """
    now_date = datetime.datetime.today()

    if room_type_id == 1:
        max_resvation_range = 15  # 최대 예약 가능 시점은 오늘부터 14일 뒤까지

    elif room_type_id == 5:
        max_resvation_range = 6  # 개방형인 경우에는 오늘부터 5일

    available_day_count = 0  # 사용 가능 일수

    # 주말이나 공휴일 등이 탐색 범위에 포함될 수 있다.
    # 예약 가능 14일, 5일을 찾기 위해선 좀 더 탐색할 필요가 존재한다.
    day_diff = iter(range(max_resvation_range + 10))  # 최대 일자 탐색 범위
    tasks = []

    while available_day_count < max_resvation_range:  # 사용 가능일이 14일을 넘으면 종료
        current_date = now_date + datetime.timedelta(
            days=next(day_diff)
        )  # 하루 씩 이동
        day = current_date.weekday()  # 요일 추출
        if (
            day > HOLIDAY
        ):  #  토:5  일:6 방학에는 주말 양일 이용이 불가하고 학기 중에는 일요일만 예약이 불가하다.
            continue

        current_date_str = current_date.strftime("%Y-%m-%d")
        task = asyncio.create_task(
            get_date_reservations(session, room_type_id, current_date_str)
        )
        tasks.append(task)
        available_day_count += 1

    results = create_results(await asyncio.gather(*tasks))

    return results


# 테스트 용
from env import *


async def get_cache_data():
    # date = "2024-04-18"  # 조회 날짜
    room_type_id = 5
    session = await create_logined_session(STUDENT_ID, USAINT_SECRET, [])
    res = await get_all_date_reservations(session, room_type_id)
    await session.close()
    return res


if __name__ == "__main__":
    print(asyncio.run(get_cache_data()))
