@echo off
SET PYTHONPATH=./common;./services/accounts
SET WEAVEFEED_ACCOUNTS_CONFIG_FILE=accounts_svc.config
SET WEAVEFEED_ACCOUNTS_CONFIG_FILE_REQUIRED=0
SET QUART_APP=services\accounts

python -m quart run -p 3030