====================================
 Serverless Step Functions Callback
====================================

This is a demo of how you can use the "callback" pattern to restart a
`Step Functions <https://aws.amazon.com/step-functions/>`_
state machine from within a Lambda function. It took me a while to dig
through the AWS docs, sample code, and examples to unlock the
mysteries, so I hope it saves you some time.

It is inspired by `Ross Rhodes' tweet on callbacks with Step Functions
<https://twitter.com/trrhodes/status/1160958680537489408>`_. He used
the AWS Cloud Development Kit and SQS, but I'll be using the
Serverless Framework with direct Lambda calls because it's a pattern
that comes up repeately in our use cases. `Ben Kehoe wrote an
excellent AWS Blog post
<https://aws.amazon.com/blogs/aws/using-callback-urls-for-approval-emails-with-aws-step-functions/>`_
on the same topic; he's using SNS Email for human approvals.

The SNS is also not exactly alined with our current use cases, but
SQS- and SNS-driven restarts are both likely something we'll need at
some point.

Our Real Use Case
=================

Our application takes a file and uses a Lambda to split it up into
chunks which are dropped onto S3. Each of those chunks' S3 ``CreateObject``
event triggers a Lambda to process the chunk, so all the chunks get
prococessed in parallel. Some chunks take longer than others, so once
we determine that all the chunks are done, we want to restart our
state machine.  We do this by calling Step Functions API directly,
indicating success.

Demo Implementation
===================

This demo code skips the complexity of our real app, allowing us to
focus on the state machine stop and restart. We'll use a random chance
to decide when we're done, with a chance that the processing function
fails, so we can signal the failure. Our state machine has a handler
for this, so it can do different things on success and failure.

Our preferred backend language is Python, so that's what we'll use for
our Lambda handler. Translating to Node or some other Lambda language
should be trivial: just map the two API calls we make to your Step
Functions SDK.

We've been using the `Serverless Framework <https://serverless.com/>`_
for a while for our commercial and government projects and really like
it: it's a pleasure to use and makes all the boring stuff go away. It
takes care of the infrastructure so we don't need to do our own
CloudFormation, nor its shiny new cousin, Cloud Development Kit.
Under the covers, Serverless does CloudFormation for us, and that's
just where it should be -- under the covers, so we can inspect it if
we need to, and ignore it most of the time. 

Takahiro Horike's `Step Function plugin
<https://github.com/horike37/serverless-step-functions>`_ for the
Serverless Framework makes it a breeze to describe state machines
directly in our ``serverless.yml`` file.

Get it Running
==============

Install the dependencies::

  npm install

Assuming you've set your AWS credentials in your environment (we set
AWS_PROFILE), deploy with Serverless; we use the default us-east-1
region and stage ``dev``::

  sls deploy

When done, you should see your functions and an HTTP endpoint we created to start the state machine::

  Serverless: Packaging service...
  ...
  Serverless: Stack update finished...
  Service Information
  service: serverless-stepfunctions-callback
  stage: dev
  region: us-east-1
  stack: serverless-stepfunctions-callback-dev
  resources: 15
  api keys:
    None
  endpoints:
  functions:
    SplitDoc: serverless-stepfunctions-callback-dev-SplitDoc
    ProcessAndCheckCompletion: serverless-stepfunctions-callback-dev-ProcessAndCheckCompletion
  layers:
    None
  Serverless StepFunctions OutPuts
  endpoints:
    GET - https://yoururlhere.execute-api.us-east-1.amazonaws.com/dev/start

In the AWS console, you should see your state machine under `Step
Functions - State machines
<https://console.aws.amazon.com/states/home#/state machines>`_.

.. image:: doc/aws-console-state machine.png
   :width: 100%

You can get details by clicking on the name; click the Definition tab to get the diagram.

.. image:: doc/state machine-diagram.png
   :width: 100%

Under the "Executions" tab, you can "Start execution", and leave the
default input alone. Depending on chance, it should go through
``ContinueProcess`` and succeed, or ``ProcessingFailed`` and fail. We
can examine the inputs and outputs of each state, so here we look at
``ContinueProcess``:

.. image:: doc/state machine-success.png
   :width: 50%
.. image:: doc/state machine-success-details.png
   :width: 45%

For the failure case, we examine at ``ProcessingFailed`` and can see
it has an ``Exception`` instead of ``Output``:

.. image:: doc/state machine-failed.png
   :width: 50%
.. image:: doc/state machine-failed-details.png
   :width: 45%

For convenience, we added an HTTP endpoint to start the state machine;
this simulates how our real application's state machine is started by
some external event, like dropping an object into S3 or a DynamoDB row
change. You can use this to start the state machine from the CLI
instead of the console::

  curl https://yoururlhere.execute-api.us-east-1.amazonaws.com/dev/start

Do this a few times then look at the console to see the results; most
will likely succeed, some will fail, due to the random chance.


On to the Code!
===============

So how does this work? How are we defining the state machine, and how
do we define the restart step, then how do we invoke it? We'll ignore
the overall state machine definition because it's well-documented, so
we can focus on the more subtle callback mechanism.

In ``serverless.yml`` we specify for the ``Resource`` the
``waitForTaskToken`` magick incantation. Normally, our state machine
would specify a Lambda function as its resource, but we can't do that
when we want to wait.  We then specify our Lambda under the
``Parameters`` as ``FunctionName``, and pass into it the ``PayLoad``
containing the Step Function ``$$.Task.Token``::

  WaitForCompletion:
    Type: Task
    Resource: arn:aws:states:::lambda:invoke.waitForTaskToken
    Parameters:
      FunctionName: ${self:service}-${opt:stage}-ProcessAndCheckCompletion
      Payload:
        taskToken.$: $$.Task.Token
    Next: ContinueProcess # the happy path

The Lambda will need to call the Step Functions API with this
``Task.Token`` to flag success or failure, so it has to be an input to
the function. We can add anything else we want as an input here too.

As usual, the state has a ``Next`` for the happy path, but here we've
defined error handlers with the ``Catch`` directive. We first try to
catch an error that we specify in our Lambda, then a catch-all in case
anything else blows up (e.g., a Python exception due to bad code)::

  Catch:
  - ErrorEquals: ["ProcessingFailed"]
    Next: ProcessingFailed
  - ErrorEquals: ["States.TaskFailed"]
    Next: UnexpectedFailure

In our Lambda handler function, we don't actually do any processing in
this demo. For the real application, we'd process our chunk and check
for all the chunks being processed; if they're not all complete, we'd
just return. Here, we pretend we have determined that all the chunks
are done, and `signal the Step Function state machine to continue
<https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions.html#SFN.Client.send_task_success>`_::

  task_token = event['taskToken']
  SFN.send_task_success(
      taskToken=task_token,
      output=json.dumps({'msg': 'this goes to the next state',
                         'status': 'looking good'}))

We can set the ``output`` to be anything we want to feed to the next
step in our state machine.

To indicate failure, we `make a similar call
<https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions.html#SFN.Client.send_task_failure>`_,
and can set optional ``error`` to a named code we can catch in our
Step Function, and the ``cause`` to provide more details::

  SFN.send_task_failure(
      taskToken=task_token,
      error='ProcessingFailed',
      cause=f'Something broke in our chunk processing chance={chance}')

If this gets executed, the ``ProcessingFailed`` should get caught by
the ``Catch... ErrorEquals: ["ProcessingFailed"]`` clause in the state
machine definition.

Conclusion
==========

We now know how to define ``waitForTaskToken`` and pass tokens ot
lambdas so they can signal success and failure to restart the
state machine, and can use it with the Serverless Framework's Step
Functions plugin with ease.  Step Functions invoke Lambdas as Tasks
asynchronously, so we may have many opportunities to have the state
machine pause and wait for completion of a longer-running lambda, or
many parallel lambdas.
