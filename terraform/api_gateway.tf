# HTTP API (v2)
resource "aws_apigatewayv2_api" "main" {
  name          = "redmine-devin"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

# POST /webhook/redmine → Lambda A
resource "aws_apigatewayv2_integration" "webhook_redmine" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.webhook_redmine.invoke_arn
  payload_format_version = "2.0"

}

resource "aws_apigatewayv2_route" "webhook_redmine" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /webhook/redmine"
  target    = "integrations/${aws_apigatewayv2_integration.webhook_redmine.id}"
}
