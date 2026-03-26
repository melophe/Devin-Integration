# Lambda 実行ロール
resource "aws_iam_role" "lambda" {
  name = "redmine-devin-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda パッケージ (デプロイ前に make package で生成)
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../build"
  output_path = "${path.module}/../lambda.zip"
}

locals {
  env_vars = {
    DEVIN_API_KEY    = var.devin_api_key
    REDMINE_URL      = var.redmine_url
    REDMINE_API_KEY  = var.redmine_api_key
    WEBHOOK_SECRET   = var.webhook_secret
  }
}

# Lambda A: Redmine Webhook → Devin起動
resource "aws_lambda_function" "webhook_redmine" {
  function_name    = "redmine-devin-webhook-redmine"
  role             = aws_iam_role.lambda.arn
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  handler          = "handlers.webhook_redmine.handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = local.env_vars
  }
}

# Lambda B: Devin完了Webhook → Redmineコメント
resource "aws_lambda_function" "webhook_devin" {
  function_name    = "redmine-devin-webhook-devin"
  role             = aws_iam_role.lambda.arn
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  handler          = "handlers.webhook_devin.handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = local.env_vars
  }
}

# API Gateway から Lambda を呼べるようにする
resource "aws_lambda_permission" "webhook_redmine" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_redmine.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "webhook_devin" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_devin.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
