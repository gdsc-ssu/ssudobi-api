import aiohttp
from aiohttp_retry import RetryClient, ExponentialRetry


async def create_retry_client(session: aiohttp.ClientSession) -> RetryClient:
    """
    연결에 문제가 발생했을 경우 재시도를 시도할 수 있게 하는 기능을
    세션에 추가합니다.

    Args:
        session (aiohttp.ClientSession): 세션

    Returns:
        RetryClient: 재시도가 가능한 세션 래핑 객체
    """
    retry_options = ExponentialRetry(
        attempts=3, statuses={401, 403, 404, 408, 429}
    )  # 리퀘스트가 너무 많은 경우, 연결 시간이 너무 긴 경우
    retry_client = RetryClient(
        raise_for_status=True, retry_options=retry_options, client_session=session
    )
    return retry_client


async def get_logined_session(token: str) -> aiohttp.ClientSession:
    """
    로그인이 반영된 비동기 세션을 생성 합니다.

    Returns:
        ClientSession: 로그인 처리가 완료된 세션
    """
    session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3))  # 세션 생성
    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "pyxis-auth-token": token,
        }
        session.headers.update(headers)

    except KeyError as e:
        raise KeyError(f">> Login failed {e}")

    return session


async def login(usaint_id: str, password: str) -> str:
    """
    로그인을 진행하고 인증 토큰을 발급합니다.

    Returns:
        str: 인증 토큰 값
    """
    login_url = "https://oasis.ssu.ac.kr/pyxis-api/api/login"  # 로그인 api
    data = {"loginId": usaint_id, "password": password}
    async with aiohttp.ClientSession() as session:
        async with session.post(login_url, json=data) as resp:
            access_token = (await resp.json())["data"]["accessToken"]  # 토큰 추출
    return access_token


if __name__ == "__main__":
    import asyncio

    res = asyncio.run(login("", "!"))
    print(res)
