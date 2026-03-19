# Use Case 2 - Get Users By Display Name

## Description

This use case narrates the process of retrieving user information based on their display name. It outlines the steps involved in querying the system for users whose display names match a given input and the expected outcomes of such queries. You have to implement edge cases like multiple users with the same display name, no users found or you don't remember the exact display name and want to do a fuzzy search. The method must return at least the user's UPN, ID, display name and email.

## APIs Endpoints

Get Users by Display Name (provide NOT exact match but also fuzzy search):

https://graph.microsoft.com/beta/users?$filter=displayName eq 'display_name'