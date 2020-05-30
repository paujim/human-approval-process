import os
import logging
import json
import email
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bucket_name = os.getenv('BUCKET_NAME')
state_machine_arn = os.getenv('STATE_MACHINE_ARN')

s3 = boto3.resource('s3')
sfn = boto3.client('stepfunctions')


def handler(event, context):

    logger.info('## EVENT')
    logger.info(event)

    records = event.get('Records', [])
    data = {}

    try:
        mail = records[0]['ses']['mail']
        message_Id = mail['messageId']
        obj = s3.Object(bucket_name, message_Id)
        body = obj.get()['Body'].read()
        msg = email.message_from_bytes(body)
        data['from'] = msg['From']
        data['subject'] = msg['Subject']
        data['message'] = msg.get_payload(0).get_payload(
        ) if msg.is_multipart else msg.get_payload().get_payload()

        sfn.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps(data)
        )

    except Exception as error:
        logger.info(str(error))

    return {
        'statusCode': 200,
    }
