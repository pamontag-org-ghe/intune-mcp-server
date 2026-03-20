# Use Case 6 - Advanced Troubleshooting On Device

## Description

This use case describes the process of advanced troubleshooting on a device in Intune. It outlines the steps involved in identifying and resolving issues with applications distributed by Intune, specifically focusing on applications that are in error state.

## Question to answer

Based on the free space on the device, can I safely perform a Feature Upgrade to Windows 11 25H2?

## APIs Endpoints

Get Info on Device by UPN:

GET https://graph.microsoft.com/beta/deviceManagement/managedDevices?$filter=(userPrincipalName eq 'mickey.mouse@velaxcrew.com')