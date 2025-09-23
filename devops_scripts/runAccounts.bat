@echo off

SETLOCAL
SET PYTHONPATH=./common;./services/accounts
SET WEAVEFEED_ACCOUNTS_CONFIG_FILE=accounts_svc.config
SET WEAVEFEED_ACCOUNTS_CONFIG_FILE_REQUIRED=false
SET QUART_APP=services\accounts

echo Setting database details... These should be customised
SET WEAVEFEED_ACCOUNTS_DB_USER=weavefeed_accounts
SET WEAVEFEED_ACCOUNTS_DB_PASSWORD=Weavefeed_2025
SET WEAVEFEED_ACCOUNTS_DB_NAME=accounts
SET WEAVEFEED_ACCOUNTS_DB_HOST=127.0.0.1

call python -m quart run -p 2222

ENDLOCAL
