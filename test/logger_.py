import logging


class MyFilter(logging.Filter):
    """Allow only LogRecords whose severity levels are below ERROR."""

    def filter(self, log):
        if log.levelno < logging.ERROR:
            return 1
        else:
            return 0


logger = logging.getLogger("TestLogger")
logger.setLevel(logging.DEBUG)  # DEBUG 레벨 이상의 모든 이벤트 기록
# 로그 핸들러 설정
error_handler = logging.FileHandler(
    "log/errors.log", mode="w"
)  # 실패한 테스트 로그 파일
error_handler.setLevel(logging.ERROR)  # ERROR 이상 로그 기록

success_handler = logging.FileHandler(
    "log/success.log", mode="w"
)  # 성공한 테스트 로그 파일
success_handler.setLevel(logging.INFO)  # INFO 이상 로그 기록
success_handler.addFilter(MyFilter())

# 로그 형식 설정
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
error_handler.setFormatter(formatter)
success_handler.setFormatter(formatter)

# 로거에 핸들러 추가
logger.addHandler(error_handler)
logger.addHandler(success_handler)
