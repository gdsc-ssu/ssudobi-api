import aiohttp
from aiohttp_retry import RetryClient, ExponentialRetry
from functools import wraps
import typing


def create_retry_client(func) -> typing.Callable:
    """
    연결에 문제가 발생했을 경우 재시도를 시도할 수 있게 하는 기능을
    세션에 추가합니다.

    Args:
        session (aiohttp.ClientSession): 세션

    Returns:
            RetryClient: 재시도가 가능한 세션 래핑 객체
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> RetryClient:
        session: aiohttp.ClientSession = await func(*args, **kwargs)
        retry_options = ExponentialRetry(
            attempts=3, statuses={401, 403, 404, 408, 429}
        )  # 리퀘스트가 너무 많은 경우, 연결 시간이 너무 긴 경우
        retry_client = RetryClient(
            raise_for_status=True, retry_options=retry_options, client_session=session
        )
        return retry_client

    return wrapper


@create_retry_client
async def create_logined_session(token: str) -> aiohttp.ClientSession:
    """
    로그인이 반영된 비동기 세션을 생성 합니다.
    Returns:
        ClientSession: 로그인 처리가 완료된 세션
    """

    url = "https://oasis.ssu.ac.kr"

    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "pyxis-auth-token": token,
        }
        session = aiohttp.ClientSession(
            base_url=url, headers=headers, timeout=aiohttp.ClientTimeout(total=3)
        )  # 세션 생성
        return session

    except aiohttp.ClientConnectionError as e:
        raise aiohttp.ClientConnectionError(f"Can't conenct {url}")


async def call_api(session: RetryClient, room_type_id: int, date: str) -> dict:
    url = f"/pyxis-api/1/api/rooms?roomTypeId={room_type_id}&smufMethodCode=PC&hopeDate={date}"
    async with session.get(url, raise_for_status=True) as response:
        try:
            response = await response.json()
            code = response.get("code", "")  # 도서관 api의 자체 응답 코드

            if (
                response.get("success") and code == "success.retrieved"
            ):  # 예약 데이터가 존재하는 경우
                return response

            raise ValueError(code)

        except aiohttp.ContentTypeError:
            raise TypeError("Response Type is not valid")
