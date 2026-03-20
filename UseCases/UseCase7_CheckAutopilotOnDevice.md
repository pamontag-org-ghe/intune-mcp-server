# Use Case 7 - Check Autopilot On Device

## Description

This use case describes the process of checking Autopilot status on a device in Intune. It outlines the steps involved in identifying and resolving issues with devices enrolled in Autopilot.

## Question to answer

Check if the device is an Autopilot device and if it has been provisioned using this method 

## APIs Endpoints

Get Autopilot Device by Serial Number:

GET https://graph.microsoft.com/beta/deviceManagement/windowsAutopilotDeviceIdentities?$filter=contains(serialNumber,'XXXXXXXXXXX')