variable "lambda_name" {
  type        = string
  description = "Lambda function name"
  default = "ecr-cleanup"
}
variable "source_file" {
  type        = string
  description = "This is source file"
  default = "ecr-cleanup.py"
}
variable "IMAGES_TO_KEEP" {
  description = "IMAGES_TO_KEEP"
  type        = number
  default     = 10
}
variable "REGION" {
  description = "Region"
  type        = string
  default     = "eu-west-2"
}
variable "DRYRUN" {
  description = "dryrun"
  type        = string
  default     = "false"
}
variable "schedule_expression" {
  description = "Cron expression to execute the lambda"
  default = "cron(0 9 1,15,30 * ? *)"
}