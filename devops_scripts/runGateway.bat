@echo off

SETLOCAL
SET PYTHONPATH=./common;./services/gateway
SET WEAVEFEED_GATEWAY_CONFIG_FILE=gateway_svc.config
SET WEAVEFEED_GATEWAY_CONFIG_FILE_REQUIRED=false
SET QUART_APP=services\gateway

call python -m quart run -p 6010

ENDLOCAL
