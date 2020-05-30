import os
import logging
import json
import boto3
import urllib
from string import Template

logger = logging.getLogger()
logger.setLevel(logging.INFO)

topic_arn = os.getenv('TOPIC_ARN')
end_point = os.getenv('END_POINT')

message = {"foo": "bar"}
client = boto3.client('sns')

email_template = None
with open("template.txt", "r") as file:
    email_template = Template(file.read())


def handler(event, context):
    logger.info('## EVENT')
    logger.info(event)

    token = event.get('token', None)
    data = event.get('data')

    approve_endpoint = end_point + \
        "/?action=approve&taskToken=" + urllib.parse.quote(token)
    reject_endpoint = end_point + \
        "/?action=reject&taskToken=" + urllib.parse.quote(token)

    email_message = email_template.substitute(
        FROM=data['from'],
        SUBJECT=data['subject'],
        MESSAGE=data['message'],
        APPROVE_URL=approve_endpoint,
        REJECT_URL=reject_endpoint,
    )

    client.publish(
        TargetArn=topic_arn,
        Message=email_message,
        Subject="Verification Required",
    )

    return {
        'statusCode': 200,
    }
