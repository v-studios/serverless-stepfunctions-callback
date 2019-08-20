====================================
 Serverless Step Functions Callback
====================================

This is a demo of how you can use "callback" pattern to restart a
`Step Functions <https://aws.amazon.com/step-functions/>`_
statemachine from within a Lambda function. It took me a while to dig
through the AWS docs, sample code, and examples to unlock the
mysteries, so I hope it saves you some time.

It is inspired by `Ross Rhodes' tweet
<https://twitter.com/trrhodes/status/1160958680537489408>`_ on the
same topic. He used the AWS Cloud Development Kit and SQS, but I'll be using the
Serverless Framework with direct Lambda calls because it's a pattern
that comes up repeately in our use cases.

`Ben Kehoe wrote an excellent AWS Blog post
<https://aws.amazon.com/blogs/aws/using-callback-urls-for-approval-emails-with-aws-step-functions/>`_
on the same topic; he's using SNS Email for human approvals.

The SNS is also not exactly alined with our current use cases, but
SQS- and SNS-driven restarts are both likely something we'll need at
some point.

Our Real Use Case
=================

Our application takes a document and uses a Lambda to split it up into
chunks which are dropped onto S3. Each of those chunks' S3 ``CreateObject``
events trigger a Lambda to process the chunk, so all the chunks get
prococessed in parallel. Some chunks take longer than others, so once
we determine that all the chunks are done, we want to restart our
state machine.  We do this by calling Step Functions API directly,
indicating success.

Demo Implementation
===================

This demo code skips the complexity of our real app, allowing us to
focus on the statemachine stop and restart. We'll use a random chance
to decide when we're done, and add to it a chance that the processing
function fails, so we can signal the failure. Our statemachine has a
handler for this, so it can do different things on success and
failure.

Our preferred backend language is Python, so that's what we'll use for
our Lambda handler. Translating to Node or some other Lambda language
should be trivial: just map the few API calls we make to your Step
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

