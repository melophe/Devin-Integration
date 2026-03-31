output "webhook_redmine_url" {
  description = "RedmineのWebhook設定に登録するURL"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/webhook/redmine"
}
