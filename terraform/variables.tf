variable "aws_region" {
  default = "ap-northeast-1"
}

variable "devin_api_key" {
  sensitive = true
}

variable "redmine_url" {}

variable "redmine_api_key" {
  sensitive = true
}

variable "webhook_secret" {
  sensitive = true
  default   = ""
}
