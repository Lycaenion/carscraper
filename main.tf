terraform {
  required_version = ">= 1.0.0" # Ensure that the Terraform version is 1.0.0 or higher

  backend "local" {
    path = "./terraform.tfstate"
  }

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
  dynamodb_code = templatefile("${path.module}/dynamodb.py", {})
  tags = {
    Project     = "CarScraper" # Tag to indicate the project name
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

    source {
        content  = local.dynamodb_code
        filename = "dynamodb.py"
    }
}

resource "aws_lambda_function" "carscraper" {
  function_name = local.lambda_function_name
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "autovia_scraper.main"
  runtime       = "python3.10"
  layers        = [aws_lambda_layer_version.deps.arn]
  tags          = local.tags
  memory_size   = "2048"
  timeout       = 300
  filename      = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  depends_on    = [aws_iam_role_policy_attachment.lambda_basic_execution]
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "${local.lambda_function_name}_exec_role"
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
  name             = "/aws/lambda/${local.lambda_function_name}"
  retention_in_days = 14
  tags              = local.tags
}

resource "null_resource" "build_layer" {
  provisioner "local-exec" {
    command = "powershell.exe -ExecutionPolicy Bypass -File ${path.module}/build_layer.ps1"
  }

  # Run again if requirements.txt changes
  triggers = {
    requirements_hash = filemd5("${path.module}/requirements.txt")
    build_script_hash = filemd5("${path.module}/build_layer.ps1")
  }
}

# Step 2: Lambda Layer (depends on the script output)
resource "aws_lambda_layer_version" "deps" {
  filename           = "${path.module}/layer.zip"
  layer_name         = "python-deps"
  compatible_runtimes = ["python3.10"]

  source_code_hash   =  base64encode(
    sha256(
      "filemd5(\"${path.module}/requirements.txt\") + filemd5(\"${path.module}/build_layer.ps1\")"
    )
  )

  depends_on = [null_resource.build_layer]
}

resource "aws_dynamodb_table" "advertisement" {
  name = "Advertisement"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "url"

  attribute {
      name = "url"
      type = "S"
  }

  attribute {
    name = "webpage_name"
    type = "S"
  }

  attribute{
      name = "brand"
      type = "S"
  }

  attribute{
    name = "year"
    type = "N"
  }

  attribute{
    name = "price"
    type = "N"
  }

  attribute{
    name = "price_brand"
    type = "S"
  }

  attribute{
    name= "price_mileage"
    type = "S"
  }

  attribute{
    name = "gearbox"
    type = "S"
  }

  attribute{
      name = "constant_key"
      type = "S"
  }

  #GSI 1 - year index
  global_secondary_index {
      name              = "yearIndex"
      hash_key          = "year"
      projection_type   = "ALL"
  }
  #GSI 2 - price index
  global_secondary_index {
      name              = "priceIndex"
      hash_key          = "price"
      projection_type   = "ALL"
  }
  #GSI 3 - year brand index
  global_secondary_index {
      name              = "yearBrandIndex"
      hash_key          = "year"
      range_key         = "brand"
      projection_type   = "ALL"
  }
  #GSI 4 - price brand index
  global_secondary_index {
      name              = "priceBrandIndex"
      hash_key          = "price_brand"
      projection_type   = "ALL"
  }
  #GSI 5 - price mileage index
  global_secondary_index {
      name              = "priceMileageIndex"
      hash_key          = "price_mileage"
      projection_type   = "ALL"
  }
  #GSI 6 - gearbox index
  global_secondary_index {
      name              = "gearboxIndex"
      hash_key          = "gearbox"
      projection_type   = "ALL"
  }
  #GSI 7 - webpage name index
  global_secondary_index {
    name            = "webpageNameIndex"
    hash_key        = "webpage_name"
    projection_type = "ALL"
  }
  #GSI 8 - year range index (for filtering between years)
  global_secondary_index {
  name            = "yearRangeIndex"
  hash_key        = "constant_key"
  range_key       = "year"
  projection_type = "ALL"
}
  tags = local.tags
}