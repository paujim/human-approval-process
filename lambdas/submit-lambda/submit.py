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
to_address = os.getenv('TO_ADDRESS')
from_address = os.getenv('FROM_ADDRESS')

message = {"foo": "bar"}
sns = boto3.client('sns')
ses = boto3.client('ses')

email_template = None
with open("template.txt", "r") as file:
    email_template = Template(file.read())
html_template = None
with open("template.html", "r") as file:
    html_template = Template(file.read())


def handler(event, context):
    logger.info('## EVENT')
    logger.info(event)

    token = event.get('token', None)
    data = event.get('data')

    approve_endpoint = end_point + \
        "/?action=approve&taskToken=" + urllib.parse.quote(token)
    reject_endpoint = end_point + \
        "/?action=reject&taskToken=" + urllib.parse.quote(token)

    data_from = data['from']
    data_subject = data['subject']
    data_message = data['message']

    email_message = email_template.substitute(
        FROM=data_from,
        SUBJECT=data_subject,
        MESSAGE=data_message,
        APPROVE_URL=approve_endpoint,
        REJECT_URL=reject_endpoint,
    )

    html_message = html_template.substitute(
        FROM=data_from,
        SUBJECT=data_subject,
        MESSAGE=data_message,
        APPROVE_URL=approve_endpoint,
        REJECT_URL=reject_endpoint,
    )

    sns.publish(
        TargetArn=topic_arn,
        Message=email_message,
        Subject="Verification Required",
    )

    ses.send_email(
        Destination={
            'BccAddresses': [],
            'CcAddresses': [],
            'ToAddresses': [to_address],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': 'UTF-8',
                    'Data': html_message,
                },
                'Text': {
                    'Charset': 'UTF-8',
                    'Data': email_message,
                },
            },
            'Subject': {
                'Charset': 'UTF-8',
                'Data': 'Verification Required',
            },
        },
        Source=from_address,
    )

    return {
        'statusCode': 200,
    }
