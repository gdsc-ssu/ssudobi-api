import redis
import boto3
import json
import traceback


def invoke_function(function_name: str, payload: dict | str):
    """
    Invokes the specified function and returns the result.
    """
    client = boto3.client("lambda")
    response = client.invoke(FunctionName=function_name, Payload=json.dumps(payload))
    return response


def get_payload(response) -> dict | None:
    try:
        payload = json.loads(response["Payload"].read().decode("utf-8"))
        status_code = payload.pop("statusCode")
        assert status_code == 200
        return payload

    except AssertionError as e:
        print("Error occured in request: ", str(e))
        raise e


def create_response(status_code: str | int, msg: str) -> dict:
    response = {
        "isBase64Encoded": False,
        "headers": {"Content-Type": "application/json"},
        "statusCode": status_code,
        "body": msg,
    }
    return response


def lambda_handler(event: dict, context: dict):
    try:
        rd = redis.Redis(
            # host="ssudobi-cache-001.96ug1w.0001.apn2.cache.amazonaws.com",
            host="localhost",
            port=6379,
            socket_timeout=3,
        )

        for room_type_id in (1, 5):
            response = invoke_function("cache", {"room_type_id": room_type_id})
            if payload := get_payload(response):
                rd.set(
                    str(room_type_id), json.dumps(payload)
                )  # set data to redis, room_type_id is key

        response = create_response(
            200,
            "Cache Success",
        )

    except Exception as e:
        response = create_response(500, str(e))
        print(traceback.format_exc())

    finally:
        return response


if __name__ == "__main__":
    lambda_handler({}, {})
