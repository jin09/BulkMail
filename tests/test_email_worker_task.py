import random
from unittest import mock

import pytest
from pydantic.v1 import EmailStr

from worker.exceptions import FailedRequestException
from worker.redis_client import RedisClient
from worker.tasks import process_and_send_email as process_and_send_email_module
from worker.tasks.process_and_send_email import set_failed_status_for_request, Status, generate_personalized_email_body, \
    set_success_status_for_email, process_and_send_email


BATCH_EMAIL_REQUEST_DATA = {
    "request_id": "88e227b5-18f5-4c6b-9578-8e25adf8598e",
    "recipients": ["test@example.com"],
    "subject": "Test Subject",
    "body": "Hello {first_name}, your email is {email}",
    "personalization_data": {
        "test@example.com": {"first_name": "John", "email": "test@example.com"}
    }
}


def test_generate_personalized_email_body():
    """
    Generates a personalized email body by replacing placeholders
    in the provided email body template with corresponding
    personalization data for the given email address.

    The function processes the input string, substitutes placeholder
    keys within curly braces with the related values from the
    personalization data dictionary for the specified email address.
    This method is useful for creating tailored email bodies for
    various recipients.

    :return: A string representing the personalized email body with
             placeholders replaced by the recipient-specific values.
    :rtype: str
    """
    email = EmailStr("test@example.com")
    body = "Hello {first_name}, your email is {email}"
    personalization_data = {
        email: {
            "first_name": "John",
            "email": "test@example.com"
        }
    }

    result = generate_personalized_email_body(email, body, personalization_data)
    expected_result = "Hello John, your email is test@example.com"
    assert result == expected_result


def test_set_failed_status_for_request():
    """
    Tests the functionality of setting the failed status for a batch email request
    in a Redis client. This function verifies that the Redis client correctly
    updates the status to 'failed' for all email recipients defined in the batch
    email request.

    The test utilizes mocks for both the Redis client and the batch email request,
    ensuring that the Redis client is called with the appropriate keys and values
    based on the given request ID and recipient email addresses. Each recipient is
    expected to have a corresponding status key in Redis with the value set to 'failed'.

    :raises AssertionError: If the Redis client does not set the status for each
        email recipient correctly or fails to call the appropriate methods with the
        expected arguments.
    """
    mock_redis_client = mock.Mock(spec=RedisClient)
    mock_redis_client.connection = mock.Mock()
    batch_email_request = mock.Mock()
    batch_email_request.recipients = ["test1@example.com", "test2@example.com"]
    batch_email_request.request_id = "12345"

    set_failed_status_for_request(batch_email_request, mock_redis_client)

    # Check that the Redis client set status to 'failed' for each email
    for email in batch_email_request.recipients:
        mock_redis_client.connection.set.assert_any_call(f"12345::{email}", str(Status.failed).encode("utf-8"))


def test_set_success_status_for_email():
    """
    Tests the functionality of setting the success status for an email in the Redis database
    by ensuring that the proper key-value pair is created in the Redis connection.

    The test verifies the interaction between the `set_success_status_for_email` function
    and the mocked Redis client by asserting that the correct `set` method is called on
    the Redis connection with the appropriate key and value.

    :return: None
    """
    mock_redis_client = mock.Mock(spec=RedisClient)
    mock_redis_client.connection = mock.Mock()
    batch_email_request = mock.Mock()
    batch_email_request.request_id = "12345"
    email = EmailStr("test@example.com")
    set_success_status_for_email(email, batch_email_request, mock_redis_client)
    mock_redis_client.connection.set.assert_called_with(f"12345::{email}", str(Status.success).encode("utf-8"))


def test_process_and_send_email_mock_failure(monkeypatch):
    """
    Tests the `process_and_send_email` function to ensure it raises a
    `FailedRequestException` when the email processing fails. The test uses
    mocking to simulate failure scenarios for essential dependent functionalities.

    :param monkeypatch: pytest's monkeypatch fixture used to mock functions
                        or attributes for controlled testing.
    :return: None
    """
    monkeypatch.setattr(random, "random", lambda: 0.0)
    monkeypatch.setattr(process_and_send_email_module, "set_failed_status_for_request", lambda _, __: ())
    with pytest.raises(FailedRequestException):
        process_and_send_email(BATCH_EMAIL_REQUEST_DATA)


def test_process_and_send_email_mock_success(monkeypatch):
    """
    Test function for mocking and testing the successful processing and sending
    of an email. This function utilizes the `monkeypatch` utility to replace
    attributes and external dependencies, allowing isolated testing of the
    `process_and_send_email` function within a controlled environment. Various
    mock objects are created to replace components such as random generation,
    logging, and RedisClient interactions.

    :param monkeypatch: pytest monkeypatch object used to dynamically modify or
        replace attributes and external dependencies during tests.
    """
    monkeypatch.setattr(random, "random", lambda: 1.0)
    mock_callable = mock.Mock()
    mock_logger = mock.Mock()
    mock_logger.info = mock.Mock()
    monkeypatch.setattr(process_and_send_email_module, "RedisClient", mock.Mock)
    monkeypatch.setattr(process_and_send_email_module, "logger", mock_logger)
    monkeypatch.setattr(process_and_send_email_module, "set_failed_status_for_request", mock_callable)
    process_and_send_email(BATCH_EMAIL_REQUEST_DATA)
    mock_logger.info.assert_called_with(f"Email Sent to {BATCH_EMAIL_REQUEST_DATA['recipients'][0]}! Subject: {BATCH_EMAIL_REQUEST_DATA['subject']} Body: {BATCH_EMAIL_REQUEST_DATA['body'].format(**BATCH_EMAIL_REQUEST_DATA['personalization_data'][BATCH_EMAIL_REQUEST_DATA['recipients'][0]])}")


def test_process_and_send_email_exception(monkeypatch):
    """
    Test case for validating the behavior of the `process_and_send_email` function
    when an exception is triggered due to missing required data in the
    `batch_request_data`. This test ensures the function raises the appropriate
    exception and handles the failure as expected, with logger and status updates.

    :param monkeypatch: A `pytest` fixture used to dynamically modify or replace
        modules, classes, or functions during the test execution.
    :return: None
    """
    batch_request_data = {
        "request_id": "88e227b5-18f5-4c6b-9578-8e25adf8598e",
        "recipients": ["test@example.com"],
        "subject": "Test Subject",
        "body": "Hello {first_name}, your email is {email}",
        "personalization_data": {
        }
    }
    monkeypatch.setattr(random, "random", lambda: 1.0)
    mock_callable = mock.Mock()
    mock_logger = mock.Mock()
    mock_logger.info = mock.Mock()
    monkeypatch.setattr(process_and_send_email_module, "RedisClient", mock.Mock)
    monkeypatch.setattr(process_and_send_email_module, "logger", mock_logger)
    monkeypatch.setattr(process_and_send_email_module, "set_failed_status_for_request", mock_callable)
    with pytest.raises(KeyError):
        process_and_send_email(batch_request_data)
