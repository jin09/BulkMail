# Bulk Mail

## Components

1. Web Server: Exposes the API for Bulk Mail
2. Celery Worker: Executes the tasks Asynchronously
3. Redis: To store the result of celery execution task
4. Rabbit-MQ: Broker b/w Server and Celery Workers

## Prerequisites

Before running this project, make sure you have the following installed on your system:

1. **Docker**  
   Install Docker by following the instructions [here](https://docs.docker.com/get-docker/).

2. **Docker Compose**  
   Install Docker Compose by following the instructions [here](https://docs.docker.com/compose/install/).

## Setup and Usage

Follow these steps to get the project up and running:

1. Clone the repository to your local machine:
   ```bash
   git clone git@github.com:jin09/BulkMail.git
   cd BulkMail
   ```

2. Build and run the Docker containers:
   ```bash
   docker-compose up --build
   ```

3. The application should now be running. Refer to specific logs in the console or project documentation for further
   usage instructions.

## Notes

- Swagger Endpoint: http://localhost:8000/docs
- RabbitMQ Management Console: http://localhost:15672/

## CURL Request:
```
curl -X 'POST' \
  'http://localhost:8000/email/batchSend' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
"recipients": ["email1@gmail.com"],
"subject": "Saying hello",
"body": "Hello {name}!",
"personalization_data": {"email1@gmail.com": {"name": "Bob"}}
}'
```