terraform {
  required_version = ">= 1.0.0" # Ensure that the Terraform version is 1.0.0 or higher

  required_providers {
    aws = {
      source = "hashicorp/aws" # Specify the source of the AWS provider
      version = "~> 4.0"        # Use a version of the AWS provider that is compatible with version
    }
    null = {
      source  = "hashicorp/null"
      version = "3.2.4"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "2.7.1"
    }
  }
}

provider "aws" {
  region = "eu-central-1" # Set the AWS region to Europe (Frankfurt)
}

locals {
  lambda_function_name = "CarScraper" # Define a local variable for the Lambda function name
  projectdb_code = templatefile("${path.module}/project_db.py", {})
  autovia_code = templatefile("${path.module}/autovia_scraper.py", {})
  autoscout24_code = templatefile("${path.module}/autoscout24_scraper.py", {})
  tags = {
    Project     = "CarScraper" # Tag to indicate the project name
  }
}

resource "null_resource" "projectdb" {
    triggers = {
        lambda_code = local.projectdb_code
    }
    provisioner "local-exec" {
        command = "echo \"${base64encode(local.projectdb_code)}\" | base64 -d" # Placeholder command for setting up the database
    }
}

resource "null_resource" "autovia" {
    triggers = {
        lambda_code = local.autovia_code
    }
    provisioner "local-exec" {
        command = "echo \"${base64encode(local.autovia_code)}\" | base64 -d" # Placeholder command for setting up the autovia scraper
    }
}

resource "null_resource" "autoscout24" {
    triggers = {
        lambda_code = local.autoscout24_code
    }
    provisioner "local-exec" {
        command = "echo \"${base64encode(local.autoscout24_code)}\" | base64 -d" # Placeholder command for setting up the autoscout24 scraper
    }
}

data "archive_file" "lambda_zip" {
  output_path = "${path.module}/${local.lambda_function_name}.zip"
  type        = "zip"

  source {
    content  = local.projectdb_code
    filename = "project_db.py"
  }

  source {
    content  = local.autovia_code
    filename = "autovia_scraper.py"
  }

    source {
        content  = local.autoscout24_code
        filename = "autoscout24_scraper.py"
    }
}

resource "aws_lambda_function" "carscraper" {
  function_name = locals.lambda_function_name
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "autovia_scraper.main"
  runtime       = "python3.13"
  layers        = []
  tags          = local.tags
  memory_size   = "2048"
  timeout       = 300
  filename      = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "${locals.lambda_function_name}_exec_role"
  tags = local.tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "log_group" {
  name             = "/aws/lambda/${locals.lambda_function_name}"
  retention_in_days = 10
  tags              = local.tags
}