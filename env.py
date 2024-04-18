from dotenv import load_dotenv
import os

# load .env
load_dotenv()

AWS_REGION = os.environ.get("AWS_REGION")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
CACHE_BUCKET = os.environ.get("CACHE_BUCKET")

STUDENT_ID = os.environ.get("STUDENT_ID")
USAINT_SECRET = os.environ.get("USAINT_SECRET")
os.environ["TZ"] = "Asia/Seoul"  # set timezone
