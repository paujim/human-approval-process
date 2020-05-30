#!/usr/bin/env python3

from aws_cdk import core

from approval_step.approval_step_stack import (
    ApprovalStepStack,
    EmailProcessingStack,
)

app = core.App()
approval_stack = ApprovalStepStack(
    scope=app,
    id="manual-approval-step")

EmailProcessingStack(
    scope=app,
    id="email-process",
    state_machine=approval_stack.get_state_machine,
)

app.synth()
