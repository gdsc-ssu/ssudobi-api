import datetime

from login_session import *

from dataclasses import dataclass, field


HOLIDAY = 5

SEMINA_ROOMS = (1, 2, 3, 4, 5, 6, 7, 9)
OPEN_SEMINA_ROOMS = (18, 21, 22, 23, 24, 25, 26)


@dataclass
class DateReservations:
    def init_data(self):
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

    def __post_init__(self):  # 값 초기화
        self.data = {x: [] for x in self.init_data()}


def call_api(session: requests.Session, room_type_id: int, date: str) -> dict:
    url = f"https://oasis.ssu.ac.kr/pyxis-api/1/api/rooms?roomTypeId={room_type_id}&smufMethodCode=PC&hopeDate={date}"
    response = session.get(url)
    response.raise_for_status()
    response = response.json()

    code = response.get("code", "")  # 도서관 api의 자체 응답 코드
    if response.get("success") == False:  # 요청이 실패한 경우
        raise ValueError(code)

    if code == "success.retrieved":  # 예약 데이터가 존재하는 경우
        return response
    else:
        raise ValueError(f"Request gor wrong {code}")


def parse_resravtions(room_type_id: int, response: dict) -> DateReservations:
    """
    json 데이터를 파싱해 시간대 별 예약 가능 여부를 갖고 있는 불리언 딕셔너리를 생성합니다.

    Args:
        time_table (dict): 예약 가능 시간 테이블
        res (requests.Response): 예약 조회 api 응답 결과

    Returns:
        dict: True인 경우 해당 시간대에 예약 가능을 의미하고 False인 경우 예약 불가능을 의미합니다.
            ex) {10: True, 11: True, 12: True, 13: True, 14: True, 15: True, 16: True, 17: True, 18: True}

    """

    room_reservations = response["data"]["list"]
    hope_date = room_reservations[0]["hopeDate"]  # 조회일자
    date_reservations = DateReservations(room_type_id=room_type_id, date=hope_date)

    for room in room_reservations:
        room_id: int = room["id"]
        room_time_lines = room["timeLine"]
        begin_hour = None

        for time_line in room_time_lines:
            minutes: list[dict] = time_line["minutes"]
            hour = time_line["hour"]
            is_reserved = (
                True
                if minutes[0]["class"]
                else False  # 첫번째 시간대만 파악하면 예약 여부를 확인 할 수 있다.
            )  # 예약 여부 확인

            if is_reserved:  # 현재 예약이 이미 차있는 경우
                if not begin_hour:
                    begin_hour = hour  # 예약 시작 시간

            elif begin_hour:
                date_reservations.data[room_id].append((begin_hour, hour))  # 예약 끝
                begin_hour = None

        if begin_hour != hour:  # 추가적으로 더 반영할 예약이 존재하는 경우
            date_reservations.data[room_id].append((begin_hour, hour))

    return date_reservations


def get_date_reservations(
    session: requests.Session,
    room_type_id: int,
    date: str,
) -> DateReservations | None:
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
        response = call_api(session, room_type_id, date)
        date_reservations = parse_resravtions(room_type_id, response)
        return date_reservations

    except Exception:
        print(
            f">> Canceled date:{date} room_number:{room_type_id}"
        )  # 실행중 에러가 발생한 경우


def get_all_date_reservations(session: requests.Session, room_type_id: int):
    #     """
    #     모든 날짜와 모든 세미나 실의 예약 현황을 조회해 현재의 예약 현황을 반환 합니다.
    #     예약 조회는 예약 가능일 기준 14일을 조회하며 이후는 조회를 하여도 예약이 불가하기 때문에 조회하지 않습니다.
    #     사용 가능일은 기준으로 하기 때문에 주말과 공휴일은 포함되지 않습니다.
    #     #TODO 공휴일 지원안됨

    #     Args:
    #         retry_client (RetryClient): 세션 객체

    #     Returns:
    #         dict: 모든 날짜 모든 세미나 실의 예약 현황 객체를 반환 합니다.
    #     """
    now_date = datetime.datetime.today()
    MAX_RESERVATION_DAY = 15  # 최대 예약 가능 시점은 현재부터 14일 뒤까지
    available_day_count = 0  # 사용 가능 일수
    day_diff = iter(range(30))  # 최대 일자 탐색 범위
    results = []
    while available_day_count < MAX_RESERVATION_DAY:  # 사용 가능일이 14일을 넘으면 종료
        current_date = now_date + datetime.timedelta(
            days=next(day_diff)
        )  # 하루 씩 이동
        day = current_date.weekday()  # 요일 추출
        if (
            day > HOLIDAY
        ):  #  토:5  일:6 방학에는 주말 양일 이용이 불가하고 학기 중에는 일요일만 예약이 불가하다.
            continue

        current_date_str = current_date.strftime("%Y-%m-%d")
        date_reservations = get_date_reservations(
            session, room_type_id, current_date_str
        )

        results.append(date_reservations)
        available_day_count += 1

    return results


# async def get_cache_data(token: str):
#     # date = "2023-08-28"  # 조회 날짜
#     # room_number = 1
#     session = await get_logined_session(token)
#     retry_client = await create_retry_client(session)

#     async with retry_client:
#         res = await get_date_reservations(retry_client, date, room_number)
#         # res = await get_all_rooms_reservation_status(retry_client, date)
#         # res = await get_all_days_reservation_status(retry_client)
#     return res


if __name__ == "__main__":
    token = "uf4asg5stjdt1das3h54m0ivo9kmulv3"
    session = get_logined_session(token)
    # print(get_date_reservations(session, 1, "2024-04-18"))
    print(get_all_date_reservations(session, 1))
