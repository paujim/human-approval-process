import os
import logging
import json
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('stepfunctions')


def handler(event, context):

    logger.info('## EVENT')
    logger.info(event)

    try:

        qs_param = event.get('queryStringParameters', None)

        if (qs_param is None):
            logger.info('Missing query string parameters')
            return {
                'statusCode': 400,
                'body': json.dumps({
                    "error": "Invalid query parameters"
                })
            }

        token = qs_param.get('taskToken', None)
        if (token is None):
            logger.info('Missing task token')
            return {
                'statusCode': 400,
                'body': json.dumps({
                    "error": "The token is required"
                })
            }

        action = qs_param.get('action', None)
        if (action is None or (action != 'approve' and action != 'reject')):
            logger.info('Invalid action')
            return {
                'statusCode': 400,
                'body': json.dumps({
                    "error": "Invalid action"
                })
            }

        respObj = {"status": "OK"} if action == 'approve' else {
            "status": "FAIL"}

        try:
            client.send_task_success(
                taskToken=token,
                output=json.dumps(respObj),
            )
            return {
                'statusCode': 200,
                'body': json.dumps(respObj)
            }
        except Exception as error:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    "error": "Something wrong",
                    "message": str(error),
                })
            }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                "error": str(e),
                "event": event,
            })
        }
