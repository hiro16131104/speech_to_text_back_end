#!/bin/bash

# ローカルで実行した場合
if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
    exec /usr/bin/aws-lambda-rie-arm64 /usr/local/bin/python -m awslambdaric $1
# aws lambda上で実行した場合
else
    exec /usr/local/bin/python -m awslambdaric $1
fi