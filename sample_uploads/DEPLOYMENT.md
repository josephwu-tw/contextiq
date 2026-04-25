# Deployment Guide

## Running with Docker

Run the application using Docker with the following command:

    docker run -p 8080:8080 contextiq-app

To pass environment variables into the container:

    docker run -p 8080:8080 -e GEMINI_API_KEY=your_key contextiq-app

## Health Check

The health check endpoint is available at GET /api/health.
It returns {"status": "ok", "version": "1.0"} when the service is running normally.

## Scaling

Horizontal scaling is supported. Set the WORKER_COUNT environment variable to
control the number of worker processes. The default is 4.

Use a load balancer to distribute requests across multiple instances.

## Logging

Application logs are written to logs/app.log by default.
Set LOG_LEVEL to DEBUG, INFO, WARNING, or ERROR to control verbosity.

To disable file logging and write only to stdout, set LOG_TO_FILE=false.

## Stopping the Service

Send a SIGTERM signal to trigger a graceful shutdown. In-flight requests will
be allowed to complete before the process exits.
