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
            attempts=3, statuses={400, 401, 403, 404, 408, 429}
        )  # 리퀘스트가 너무 많은 경우, 연결 시간이 너무 긴 경우
        # 명확하게 해당 코드가 전달된 경우만 재시도
        retry_client = RetryClient(
            raise_for_status=True, retry_options=retry_options, client_session=session
        )
        return retry_client

    return wrapper


@create_retry_client
async def create_logined_session(
    student_id: str, usaint_secret: str, tokens: list
) -> aiohttp.ClientSession:
    """
    로그인을 진행하고 인증 토큰을 발급합니다.

    Returns:
        str: 인증 토큰 값
    """

    session = aiohttp.ClientSession(
        base_url="https://oasis.ssu.ac.kr",
        timeout=aiohttp.ClientTimeout(total=3),
        raise_for_status=True,
    )
    login_url = "/pyxis-api/api/login"  # 로그인 api
    payload = {
        "loginId": student_id,
        "password": usaint_secret,
        "isFamilyLogin": False,
        "isMobile": False,
    }

    if len(tokens):
        token = tokens.pop()

    else:
        async with session.post(login_url, json=payload) as resp:
            if resp is None:
                raise ValueError("Incorrect Response")
            json_res = await resp.json()  # 토큰 추출

        assert json_res["success"], "Login Failed"  # 로그인 성공 확인
        token = json_res["data"]["accessToken"]

    headers = {
        "Accept": "application/json, text/plain, */*",
        "pyxis-auth-token": token,
    }

    session.headers.update(headers)
    tokens.append(token)
    return session


async def call_reservation_api(
    session: RetryClient, room_type_id: int, date: str
) -> dict:
    url = f"/pyxis-api/1/api/rooms?roomTypeId={room_type_id}&smufMethodCode=PC&hopeDate={date}"
    async with session.get(url) as response:
        try:
            response = await response.json()
            is_success = response.get("success")  # 도서관 api의 자체 응답 코드
            if is_success:  # 예약 데이터가 존재하는 경우
                return response
            else:
                raise AssertionError("Token expired")

        except aiohttp.ContentTypeError:
            raise TypeError("Response Type is not valid")

        except Exception as e:
            raise Exception("Error Occured in call api", str(e))
