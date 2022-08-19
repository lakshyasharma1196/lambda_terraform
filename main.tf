locals{
    lambda_zip_location = "outputs/ecr-cleanup.zip"
}

data "archive_file" "ecr-cleanup" {
  type        = "zip"
  source_file = "${var.source_file}"
  output_path = "${local.lambda_zip_location}"
}


resource "aws_lambda_function" "lambda" {

  filename      = "${local.lambda_zip_location}"
  function_name = "${var.lambda_name}"
  role          = "${aws_iam_role.lambda_role.arn}"
  handler       = "ecr-cleanup.lambda_handler"


  source_code_hash = "${filebase64sha256(local.lambda_zip_location)}"

  runtime = "python3.7"

    environment {
    variables = {
      IMAGES_TO_KEEP = var.IMAGES_TO_KEEP
      REGION = var.REGION
      DRYRUN = var.DRYRUN
    }
  }

}
resource "aws_lambda_permission" "cloudwatch_trigger" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${var.lambda_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.ecr-cleanup-event.arn}"
}

resource "aws_cloudwatch_event_rule" "ecr-cleanup-event" {
  name                = "ecr-cleanup-event"
  description         = "Schedule trigger for lambda execution"
  schedule_expression = "${var.schedule_expression}"
}

resource "aws_cloudwatch_event_target" "ecr-cleanup-event" {
  target_id = "ecr-cleanup-event"
  rule      = aws_cloudwatch_event_rule.ecr-cleanup-event.name
  arn       = aws_lambda_function.lambda.arn
}