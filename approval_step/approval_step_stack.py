import constants
import uuid
import os
import typing
from aws_cdk import (
    core,
    aws_iam as iam,
    aws_cognito as cognito,
    aws_apigateway as apigateway,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_ses as ses,
    aws_ses_actions as actions,
    aws_s3 as s3,
)


def _random_ApiKey(file_name: str) -> str:
    if os.path.exists(file_name):
        with open("api.key", "r") as file:
            return file.read()
    else:
        api_key = uuid.uuid4().hex.upper()
        with open("api.key", "w") as file:
            file.write(api_key)
        return api_key


class ApprovalStepStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        api = apigateway.RestApi(
            scope=self,
            id=f'{constants.PREFIX}-approval-api',
            rest_api_name='Human approval endpoint',
            description='HTTP Endpoint backed by API Gateway and Lambda',
            endpoint_types=[apigateway.EndpointType.REGIONAL],
        )

        v1 = api.root.add_resource("v1")
        approve_api = v1.add_resource("approve")

        #################################################

        email_topic = sns.Topic(
            scope=self,
            id=f'{constants.PREFIX}-email-topic',
        )
        email_topic.add_subscription(
            subscription=subscriptions.EmailSubscription(
                email_address=constants.EMAIL_APPROVER,
            ))

        #################################################

        submit_job_lambda = _lambda.Function(
            scope=self,
            id=f'{constants.PREFIX}-submit-lambda',
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='submit.handler',
            environment={
                "TOPIC_ARN": email_topic.topic_arn,
                "END_POINT": approve_api.url,
            },
            code=_lambda.Code.from_asset(
                os.path.join('lambdas', 'submit-lambda')),
        )

        email_topic.grant_publish(submit_job_lambda)

        submit_job = tasks.LambdaInvoke(
            scope=self,
            id=f'{constants.PREFIX}-submit-job',
            lambda_function=submit_job_lambda,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            heartbeat=core.Duration.minutes(5),
            payload=sfn.TaskInput.from_object({
                "token": sfn.Context.task_token,
                "data": sfn.Data.string_at('$'),
            }),
        )

        success = sfn.Succeed(
            scope=self,
            id=f'{constants.PREFIX}-success',
            comment='We did it!')
        fail = sfn.Fail(
            scope=self,
            id=f'{constants.PREFIX}-fail',
            error='WorkflowFailure',
            cause='Something went wrong'
        )

        choice = sfn.Choice(
            scope=self,
            id=f'{constants.PREFIX}-choice',
            comment='Was it approved?')

        choice.when(condition=sfn.Condition.string_equals(
            "$.status", "OK"), next=success)
        choice.otherwise(fail)

        definition = submit_job.next(choice)

        self._state_machine = sfn.StateMachine(
            scope=self,
            id=f'{constants.PREFIX}-state-machine',
            definition=definition,
            # only 10 mins to approve better be quick
            timeout=core.Duration.minutes(10)
        )

        #################################################

        approval_lambda = _lambda.Function(
            scope=self,
            id=f'{constants.PREFIX}-approval-lambda',
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='approve.handler',
            code=_lambda.Code.from_asset(
                os.path.join('lambdas', 'approve-lambda')),
        )
        approval_lambda.add_to_role_policy(
            statement=iam.PolicyStatement(
                actions=['states:Send*'],
                resources=['*'])
        )

        approve_integration = apigateway.LambdaIntegration(
            approval_lambda)

        approve_api_get_method = approve_api.add_method(
            http_method="GET",
            api_key_required=False,
            integration=approve_integration,
        )

    @property
    def get_state_machine(self) -> sfn.StateMachine:
        return self._state_machine


class EmailProcessingStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, state_machine: sfn.StateMachine, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        email_bucket = s3.Bucket(
            scope=self,
            id=f'{constants.PREFIX}-email-bucket',
            removal_policy=core.RemovalPolicy.DESTROY,
        )

        process_email_lambda = _lambda.Function(
            scope=self,
            id=f'{constants.PREFIX}-process-email-lambda',
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='process.handler',
            code=_lambda.Code.from_asset(
                os.path.join('lambdas', 'process-email-lambda')),
            environment={
                "BUCKET_NAME": email_bucket.bucket_name,
                "STATE_MACHINE_ARN": state_machine.state_machine_arn,
            },
        )
        email_bucket.grant_read(process_email_lambda)
        state_machine.grant_start_execution(process_email_lambda)

        ses.ReceiptRuleSet(
            scope=self,
            id=f'{constants.PREFIX}-rule-set',
            rules=[
                ses.ReceiptRuleOptions(
                    recipients=[constants.EMAIL_RECIPIENT],
                    actions=[
                        actions.S3(bucket=email_bucket),
                        actions.Lambda(function=process_email_lambda),
                    ]),
            ],
        )
