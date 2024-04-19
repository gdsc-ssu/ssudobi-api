from dotenv import load_dotenv
import os

# load .env
# load_dotenv()

AWS_REGION_NAME = os.environ["AWS_REGION_NAME"]
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
CACHE_BUCKET = os.environ["CACHE_BUCKET"]

STUDENT_ID = os.environ["STUDENT_ID"]
USAINT_SECRET = os.environ["USAINT_SECRET"]

envs = (
    AWS_REGION_NAME,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    CACHE_BUCKET,
    STUDENT_ID,
    USAINT_SECRET,
)
