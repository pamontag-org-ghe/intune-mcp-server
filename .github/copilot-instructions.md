# Scope of the project

Implementing an MCP server that can receive and process requests from the MCP client, and return appropriate responses based on the defined use cases. The MCP server will expose Intune Graph API endpoints that the MCP client can interact with to retrieve policies associated with specific devices. The server will be designed to handle requests efficiently and securely, ensuring that it can scale to meet the demands of the client applications. You will get use cases in folder UseCases, and you need to implement the MCP server to support those use cases.

# Deployment

The MCP Server must be deployed as Streamable Http Endpoints. The MCP Server will be hosted on Azure, and the deployment process will involve setting up the necessary infrastructure, configuring the server environment, and ensuring that the endpoints are accessible for the MCP client to interact with. The deployment will also include monitoring and maintenance strategies to ensure the server's performance and availability over time. You must provide deployment scripts for deploy the Azure resources needed for the MCP server, and also provide scripts for deploying the MCP server itself. The deployment scripts should be well-documented and easy to use, allowing for seamless deployment of the MCP server on Azure.

# Frameworks and Libraries

You can choose python as language and use FastAPI as the web framework for building the MCP server. FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints. It is designed to be easy to use and to provide high performance, making it a great choice for building the MCP server.

# Containerization

It be recommended to containerize the MCP server using Docker. Nice to have to be deployed on Azure Container Apps on a brand new resource. Containerization will allow for easier deployment, scalability, and management of the MCP server. By using Docker, you can create a consistent environment for the server, ensuring that it runs smoothly across different platforms and environments. Additionally, deploying on Azure Container Apps will provide benefits such as automatic scaling, load balancing, and seamless integration with other Azure services.

# Monitoring

Implement monitoring with Application Insights to track the performance and health of the MCP server. This will allow you to identify and troubleshoot any issues that may arise, as well as gain insights into usage patterns and performance metrics. You can set up Application Insights in Azure and integrate it with your FastAPI application to collect telemetry data, such as request rates, response times, and exceptions. This will help you ensure that the MCP server is running smoothly and efficiently.

# Authentication

You can authenticate against Intune using an App Registration with client_id, client_secret and tenant_id info that will be injected as environment variables. The MCP server will use these credentials to authenticate with the Intune Graph API and retrieve the necessary data for the defined use cases. You can implement authentication using the Microsoft Authentication Library (MSAL) for Python, which provides a simple and secure way to acquire tokens for accessing Microsoft Graph API. By using environment variables to store sensitive information, you can ensure that your credentials are kept secure and are not hard-coded in your application. 