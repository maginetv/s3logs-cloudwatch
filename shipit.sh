#!/bin/bash

zip s3logs-cloudwatch.zip lambda_function.py configuration.ini
aws lambda update-function-code --function-name s3logs-cloudwatch --zip-file fileb://s3logs-cloudwatch.zip --publish
rm s3logs-cloudwatch.zip
