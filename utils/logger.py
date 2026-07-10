import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from utils.path_handler import get_app_data_path

# 로그 폴더 설정
LOG_DIR = get_app_data_path("logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 로거 이름 설정
LOGGER_NAME = "WaveSurfer"
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)  # 모든 로그를 수집 (필터링은 핸들러에서 수행)

# 1. 파일 핸들러 (TimedRotatingFileHandler)
# - 매일 자정(midnight)에 새 파일 생성
# - backupCount=7 (최근 7일치 보관)
file_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOG_DIR, "app.log"),
    when="midnight",
    interval=1,
    backupCount=7,
    encoding="utf-8"
)
file_handler.setLevel(logging.INFO)  # 파일에는 INFO 이상만 기록

# 2. 콘솔 핸들러 (개발용 터미널 출력)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # 콘솔에는 디버그 로그까지 출력

# 3. 포맷터 설정
# [%(threadName)s]를 포함하여 멀티스레드 환경 분석 용이성 확보
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s", 
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 4. 핸들러 추가
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def log_info(msg):
    logger.info(msg)

def log_error(msg):
    logger.error(msg)

def log_debug(msg):
    logger.debug(msg)

def log_exception(msg):
    """예외 발생 시 상세 Stacktrace를 포함하여 기록"""
    logger.exception(msg)

def setup_global_exception_handler():
    """예기치 않은 시스템 에러(Unhandled Exception)를 로그에 기록하도록 설정"""
    def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # 사용자가 강제 종료(Ctrl+C)한 경우 기본 동작 수행
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("🚨 Unhandled Exception occurred!", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_unhandled_exception
    logger.info("✅ Global exception handler has been installed.")

def shutdown_logger():
    """앱 종료 시 로깅 핸들러 락을 완전히 해제하여 파일 공유 위반 에러 방지"""
    try:
        logging.shutdown()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
    except Exception as e:
        print(f"Error shutting down logger: {e}")
