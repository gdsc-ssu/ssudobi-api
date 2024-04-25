import json
import redis
import traceback


def create_response(status_code: str | int, cache: str | bytes) -> dict:
    response = dict(
        {
            "isBase64Encoded": False,
            "headers": {"Content-Type": "application/json"},
            "statusCode": status_code,
            "body": cache,
        },
    )
    return response


def lambda_handler(event: dict, context: dict):
    try:
        rd = redis.Redis(
            # host="ssudobi-cache-001.96ug1w.0001.apn2.cache.amazonaws.com",
            host="localhost",
            port=6379,
            socket_timeout=3,
        )
        room_type_id = event["pathParameters"].get("room_type_id", "1")
        cache = rd.get(room_type_id)  # set data to redis
        response = create_response(200, cache)

    except Exception as e:
        response = create_response(500, str(e))
        print(traceback.format_exc())

    finally:
        return response


if __name__ == "__main__":
    print(lambda_handler({"pathParameters": {"room_type_id": "1"}}, {}))
