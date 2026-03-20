# Use Case 9 - Get Policies Impacted from Device Not Compliant

## Description

This use case describes the process of retrieving compliance policies that are impacted when a device is not compliant in Intune. It outlines the steps involved in identifying and resolving compliance issues on devices.

## Question to answer

Which compliance policies are impacted when the device is not compliant?

## APIs Endpoints

Get Compliance Policies Impacted by Device Non-Compliance:
(IMPORTANT - IS JUST AN EXAMPLE)

GET https://graph.microsoft.com/beta/identity/conditionalAccess/policies?$filter=contains(conditions/devices, 'DEVICEID') and contains(conditions/applications, 'All') and state eq 'enabled'





