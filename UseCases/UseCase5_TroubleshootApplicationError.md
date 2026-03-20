# Use Case 5 - Troubleshoot Application Error

## Description

This use case describes the process of troubleshooting application errors in Intune. It outlines the steps involved in identifying and resolving issues with applications distributed by Intune.

## Question to answer

An app 'Application Name' is in error, what is the problem reported by the error code if available?  

## APIs Endpoints

Get Applications distributed by Intune:

POST https://graph.microsoft.com/beta/deviceManagement/reports/microsoft.graph.retrieveDeviceAppInstallationStatusReport

{
  "select": [
    "DeviceName",
    "DeviceId",
    "UserPrincipalName",
    "Platform",
    "AppVersion",
    "InstallState",
    "InstallStateDetail",
    "ErrorCode",
    "HexErrorCode",
    "LastModifiedDateTime",
    "UserName",
    "UserId",
    "ApplicationId",
    "AppInstallState",
    "AppInstallStateDetails"
  ],
  "skip": 0,
  "top": 50,
  "filter": "(ApplicationId eq 'fd51e121-39a8-4bcc-982b-c261fb0eb1c0')",
  "orderBy": []
}