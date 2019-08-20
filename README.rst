===================================
 Serverless Stepfunctions Callback
===================================

This is a demo of how you can use "callback" pattern to restart a
StepFunctions statemachine from within a Lambda function. It took me a
while to dig through the AWS docs, sample code, and examples to unlock
the mysteries, so I hope it saves you some time.

It is inspired by Ross Rhodes' tweet on the same topic:

https://twitter.com/trrhodes/status/1160958680537489408

He used the AWS Cloud Development Kit and SQS, but I'll be using the
Serverless Framework with direct Lambda calls because it's a pattern
that comes up repeately in our use cases.

Ben Kehoe has an excellent AWS Blog post on the same topic, and he's
using SNS Email for human approvals:

https://aws.amazon.com/blogs/aws/using-callback-urls-for-approval-emails-with-aws-step-functions/

The SNS is also not exactly alined with our current use cases, but
SQS- and SNS-driven restarts are both likely something we'll need at
some point.

Our application takes a document and uses a Lambda to split it up into
chunks which are dropped onto S3; each of those chunk CreateObject
events trigger a Lambda to process the chunk, so all the chunks get
prococessed in parallel. Some chunks take longer than others, so once
we determine that all the chunks are done, we want to restart our
state machine.  We do this by calling StepFunction API directly,
indicating success.

This demo code skips the complexity of our real app, allowing us to
focus on the statemachine stop and restart.  We add to it a chance
that the processing function may fail, so we signal the failure. Our
statemachine has a handler for this failure, so it can do different
things on success and failure.

