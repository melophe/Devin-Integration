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


# Lambda A が Worker Lambda を invoke できるポリシー
resource "aws_iam_role_policy" "lambda_invoke_worker" {
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.worker.arn
    }]
  })
}

# Lambda パッケージ
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../build"
  output_path = "${path.module}/../lambda.zip"
}

locals {
  env_vars_webhook = {
    DEVIN_API_KEY          = var.devin_api_key
    REDMINE_URL            = "http://${aws_instance.redmine.public_ip}:3000"
    REDMINE_API_KEY        = var.redmine_api_key
    WEBHOOK_SECRET         = var.webhook_secret
    WORKER_FUNCTION_NAME   = aws_lambda_function.worker.function_name
  }

  env_vars_worker = {
    DEVIN_API_KEY   = var.devin_api_key
    REDMINE_URL     = "http://${aws_instance.redmine.public_ip}:3000"
    REDMINE_API_KEY = var.redmine_api_key
  }
}

# Lambda A: Webhook受信 → @devin検知 → Workerを非同期起動 → 即200返す
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
    variables = local.env_vars_webhook
  }
}

# Lambda Worker: Devin起動 → ポーリング → Redmineにコメント
resource "aws_lambda_function" "worker" {
  function_name    = "redmine-devin-worker"
  role             = aws_iam_role.lambda.arn
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  handler          = "handlers.worker.handler"
  runtime          = "python3.12"
  timeout          = 900  # 15分
  memory_size      = 256

  environment {
    variables = local.env_vars_worker
  }
}

# API Gateway から Lambda A を呼べるようにする
resource "aws_lambda_permission" "webhook_redmine" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_redmine.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
