from datetime import datetime
import json

import boto3
import pytz


def create_response(status_code: str | int, msg: str) -> dict:
    response = {
        "isBase64Encoded": False,
        "headers": {"Content-Type": "application/json"},
        "statusCode": status_code,
        "body": msg,
    }
    return response


def read_json_from_s3(bucket_name: str, file_key: str):
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket_name, Key=file_key)

    object_data = json.loads(response["Body"].read())  # json 파일 정보
    meta_data = response["LastModified"]  # 최종 캐싱 시간

    last_cached_time = meta_data.astimezone(pytz.timezone("Asia/Seoul"))  # UTC -> Seoul
    last_cached_time = datetime.strftime(
        last_cached_time, "%Y-%m-%d %H:%M:%S"
    )  # datetime -> str
    return last_cached_time, object_data


def handler(event=None, context=None):
    response = create_response(200, "")
    bucket_name = "ssudobi-cache"
    file_key = "cache"
    try:
        last_cached_time, data = read_json_from_s3(bucket_name, file_key)
        response = create_response(
            200, json.dumps({"last_cached_time": last_cached_time, "data": data})
        )

    except Exception as e:
        response = create_response(500, json.dumps({"error": str(e)}))

    finally:
        return response


# print(read_json_from_s3("ssudobi-cache", "cache"))
# print(handler())
