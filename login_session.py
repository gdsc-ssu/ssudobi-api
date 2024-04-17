import requests

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


def get_logined_session(token: str) -> requests.Session:
    """
    로그인을 진행하고 인증 토큰을 발급합니다.

    Returns:
        str: 인증 토큰 값
    """
    session = requests.Session()
    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Pyxis-Auth-Token": token,
        }
        session.headers.update(headers)
        return session

    except AssertionError as e:
        session.close()
        raise e
