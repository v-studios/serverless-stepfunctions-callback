import json
from random import random

import boto3

SFN = boto3.client('stepfunctions')


def split_doc(event, context):
    print(f'split_doc: simulate initial processing by splitting the doc')
    return {'msg': 'OK, the doc is split; next each chunk should be processed'}


def process_and_check_completion(event, context):
    print(f'# event={json.dumps(event)}')
    task_token = event['taskToken']  # named by the state machine Payload
    print(f'Simulate processing a chunk and check for all chunks done...')
    # In a real application, we'd process a chunk and check if they're all
    # done; if they are not all completed, we'd just exit without triggering
    # the state machine; here, we pretend we're done, or maybe we encountered
    # an error.
    chance = random()
    if chance < 0.7:            # most of the time we succeed
        print(f'Great, our chunks finished ok, restart the machine happy path')
        SFN.send_task_success(
            taskToken=task_token,
            output=json.dumps({'msg': 'this goes to the next state',
                               'status': 'looking good'}))
    else:                       # but randomly simuate a failure
        SFN.send_task_failure(
            taskToken=task_token,
            error='ProcessingFailed',  # match in state machine ErrorEquals
            cause=f'Something broke in our chunk processing chance={chance}')
