@echo off

SETLOCAL
SET PYTHONPATH=./common;./services/accounts
SET WEAVEFEED_ACCOUNTS_CONFIG_FILE=accounts_svc.config
SET WEAVEFEED_ACCOUNTS_CONFIG_FILE_REQUIRED=false
SET QUART_APP=services\accounts

call python -m quart run -p 2222

ENDLOCAL
