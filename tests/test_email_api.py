import asyncio
import pytest
from unittest import mock

from aiormq import AMQPError
from fastapi.testclient import TestClient
from fastapi import status
from kombu.exceptions import KombuError

from app.api.email import router
from app.main import app
from models import StatusEnum
from worker.tasks import process_and_send_email


# Sample input data
VALID_BODY_DATA = {
    "recipients": ["email1@gmail.com"],
    "subject": "Saying hello",
    "body": "Hello {name}!",
    "personalization_data": {"email1@gmail.com": {"name": "Bob"}}
}


@pytest.fixture
def client():
    """
    Fixture to create and return a test client instance for the application.

    This client can be used to simulate HTTP requests to the application
    during test execution. It provides a controlled environment for
    testing API behavior without requiring a live server.

    :return: TestClient instance to interact with the app during tests
    :rtype: TestClient
    """
    return TestClient(app)


async def mock_run_in_executor(_, __, *___, **____):
    return mock.Mock()


# Test the happy path where process_and_send_email.apply_async is successful
def test_email_batch_send_success(client, monkeypatch):
    """
    Tests the successful execution of the batch email sending endpoint by mocking
    related asynchronous calls, overriding necessary request handling behaviors,
    and verifying the response status and data with expected values.

    :param client: A pytest fixture that simulates a TestClient for making HTTP
        requests.
    :param monkeypatch: A pytest fixture that enables modification of behavior for
        imported modules and objects.
    :return: None
    """
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: mock.Mock(run_in_executor=mock_run_in_executor))

    monkeypatch.setattr(router, "get_request_id", lambda _: "88e227b5-18f5-4c6b-9578-8e25adf8598e")

    # Send a POST request to the /email/batchSend endpoint
    response = client.post("/email/batchSend", json=VALID_BODY_DATA)

    # Assert the response status code
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"status": StatusEnum.submitted,
                               "request_id": "88e227b5-18f5-4c6b-9578-8e25adf8598e"}


def test_email_batch_send_amqp_error(client, monkeypatch):
    """
    Test case to verify the behavior of the email batch sending functionality when there is an
    AMQPError during the process. This test mocks critical functions to simulate an AMQPError
    and ensures that the service responds appropriately with a 503 Service Unavailable status
    along with the correct error details.

    :param client: Test client that is used to simulate API requests for testing purposes
    :type client: TestClient
    :param monkeypatch: Pytest utility used to dynamically replace or mock parts of the
        system during tests
    :type monkeypatch: MonkeyPatch
    :return: None
    """
    monkeypatch.setattr(process_and_send_email.process_and_send_email, "apply_async",
                        lambda **kwargs: (_ for _ in ()).throw(AMQPError))

    monkeypatch.setattr(router, "get_request_id", lambda _: "88e227b5-18f5-4c6b-9578-8e25adf8598e")

    # Send a POST request to the /email/batchSend endpoint
    response = client.post("/email/batchSend", json=VALID_BODY_DATA)

    # Assert the response status code
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {'detail': {"status": StatusEnum.errored, "error_message": "",
                                          "request_id": "88e227b5-18f5-4c6b-9578-8e25adf8598e"}}


def test_email_batch_send_kombu_error(client, monkeypatch):
    """
    This function tests the `/email/batchSend` endpoint when a KombuError is raised during the
    email batch processing. It validates that the correct error response is returned to the
    client with the appropriate status code and error details.

    :param client: A test client used to send HTTP requests to the application.
    :type client: FlaskClient or TestClient (appropriate testing client instance)
    :param monkeypatch: A pytest fixture that allows modification of objects for testing purposes.
    :type monkeypatch: MonkeyPatch
    :return: None
    """
    # Sample input data
    body_data = {
        "recipients": ["email1@gmail.com"],
        "subject": "Saying hello",
        "body": "Hello {name}!",
        "personalization_data": {"email1@gmail.com": {"name": "Bob"}}
    }

    # Request mock
    monkeypatch.setattr(process_and_send_email.process_and_send_email, "apply_async",
                        lambda **kwargs: (_ for _ in ()).throw(KombuError))

    monkeypatch.setattr(router, "get_request_id", lambda _: "88e227b5-18f5-4c6b-9578-8e25adf8598e")

    # Send a POST request to the /email/batchSend endpoint
    response = client.post("/email/batchSend", json=body_data)

    # Assert the response status code
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {'detail': {"status": StatusEnum.errored, "error_message": "",
                                          "request_id": "88e227b5-18f5-4c6b-9578-8e25adf8598e"}}


def test_bad_recipient_email_id(client, monkeypatch):
    """
    Tests the scenario where the recipient email provided in the batch send request is invalid,
    ensuring the system returns an appropriate HTTP 422 response code.

    This test validates that the email validation logic detects invalid email formats under
    batch send email operations, maintaining data integrity and preventing erroneous processing
    of email recipients.

    :param client: The test client used to simulate an API request.
    :type client: starlette.testclient.TestClient
    :param monkeypatch: The fixture used to dynamically replace attributes during testing.
    :type monkeypatch: pytest.MonkeyPatch
    :return: None. This function performs assertions for test validation.
    :rtype: None
    """
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: mock.Mock(run_in_executor=mock_run_in_executor))

    # Sample input data
    body_data = {
        "recipients": ["not an email"],
        "subject": "Saying hello",
        "body": "Hello {name}!",
        "personalization_data": {"email1@gmail.com": {"name": "Bob"}}
    }

    # Request mock
    monkeypatch.setattr(process_and_send_email.process_and_send_email, "apply_async", mock.Mock())

    monkeypatch.setattr(router, "get_request_id", lambda _: "88e227b5-18f5-4c6b-9578-8e25adf8598e")

    # Send a POST request to the /email/batchSend endpoint
    response = client.post("/email/batchSend", json=body_data)

    # Assert the response status code
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_missing_recipient_field(client, monkeypatch):
    """
    Tests the scenario where a required recipient field is missing in the input data for the
    batch email sending functionality. This test verifies that the application handles the
    missing field properly by returning the correct HTTP status code. Mocks are incorporated
    to simulate external dependencies and asynchronous behavior during the test execution.

    :param client: Test client simulating API interaction.
    :type client: TestClient
    :param monkeypatch: Provides mocking capabilities for altering or replacing attributes during testing.
    :type monkeypatch: MonkeyPatch
    :return: None
    :rtype: None
    """
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: mock.Mock(run_in_executor=mock_run_in_executor))

    # Sample input data
    body_data = {
        "subject": "Saying hello",
        "body": "Hello {name}!",
        "personalization_data": {"email1@gmail.com": {"name": "Bob"}}
    }

    # Request mock
    monkeypatch.setattr(process_and_send_email.process_and_send_email, "apply_async", mock.Mock())

    monkeypatch.setattr(router, "get_request_id", lambda _: "88e227b5-18f5-4c6b-9578-8e25adf8598e")

    # Send a POST request to the /email/batchSend endpoint
    response = client.post("/email/batchSend", json=body_data)

    # Assert the response status code
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_missing_subject_field(client, monkeypatch):
    """
    Tests the behavior of the batch email sending endpoint when the subject field is
    missing in the request payload. The test verifies that the server responds with
    an HTTP 422 Unprocessable Entity status code in such a scenario.

    The function utilizes monkey patching to mock certain functionalities, such as
    the event loop, task queuing, and request ID generation, ensuring isolation of
    tests and realistic emulation of dependencies.

    :param client: A test client that simulates the HTTP request to the batch email
                   sending endpoint.
    :type client: fastapi.testclient.TestClient
    :param monkeypatch: A pytest fixture used to dynamically modify or replace
                        parts of the code for testing purposes.
    :type monkeypatch: pytest.MonkeyPatch
    :return: None
    """
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: mock.Mock(run_in_executor=mock_run_in_executor))

    # Sample input data
    body_data = {
        "recipients": ["email1@gmail.com"],
        "body": "Hello {name}!",
        "personalization_data": {"email1@gmail.com": {"name": "Bob"}}
    }

    # Request mock
    monkeypatch.setattr(process_and_send_email.process_and_send_email, "apply_async", mock.Mock())

    monkeypatch.setattr(router, "get_request_id", lambda _: "88e227b5-18f5-4c6b-9578-8e25adf8598e")

    # Send a POST request to the /email/batchSend endpoint
    response = client.post("/email/batchSend", json=body_data)

    # Assert the response status code
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_missing_body_field(client, monkeypatch):
    """
    Tests the behavior of the `/email/batchSend` endpoint when a required body field
    is missing. The test verifies that the endpoint correctly identifies the missing
    field and returns an appropriate HTTP 422 Unprocessable Entity status code. It
    utilizes mock objects and monkeypatching to isolate and simulate component
    dependencies during the test execution.

    :param client: A test client instance for simulating HTTP requests.
    :type client: flask.testing.FlaskClient
    :param monkeypatch: Pytest fixture used to dynamically modify attributes or
        behaviors during the test run.
    :type monkeypatch: _pytest.monkeypatch.MonkeyPatch
    :return: None
    :rtype: None
    """
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: mock.Mock(run_in_executor=mock_run_in_executor))

    # Sample input data
    body_data = {
        "subject": "Saying hello",
        "recipients": ["email1@gmail.com"],
        "personalization_data": {"email1@gmail.com": {"name": "Bob"}}
    }

    # Request mock
    monkeypatch.setattr(process_and_send_email.process_and_send_email, "apply_async", mock.Mock())

    monkeypatch.setattr(router, "get_request_id", lambda _: "88e227b5-18f5-4c6b-9578-8e25adf8598e")

    # Send a POST request to the /email/batchSend endpoint
    response = client.post("/email/batchSend", json=body_data)

    # Assert the response status code
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_missing_personalization_data_field(client, monkeypatch):
    """
    Tests the email batch sending functionality with missing personalization data.
    Ensures that when the personalization data field is missing in the request body,
    the HTTP response status is 422 Unprocessable Entity.

    :param client: A test client instance used to send requests to the application.
    :type client: TestClient
    :param monkeypatch: A pytest fixture for safely patching and mocking objects.
    :type monkeypatch: _pytest.monkeypatch.MonkeyPatch
    :return: None
    :rtype: None
    """
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: mock.Mock(run_in_executor=mock_run_in_executor))

    # Sample input data
    body_data = {
        "subject": "Saying hello",
        "recipients": ["email1@gmail.com"],
        "body": "Hello {name}!",
    }

    # Request mock
    monkeypatch.setattr(process_and_send_email.process_and_send_email, "apply_async", mock.Mock())

    monkeypatch.setattr(router, "get_request_id", lambda _: "88e227b5-18f5-4c6b-9578-8e25adf8598e")

    # Send a POST request to the /email/batchSend endpoint
    response = client.post("/email/batchSend", json=body_data)

    # Assert the response status code
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
