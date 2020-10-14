from hypothesis import example, given
from hypothesis.strategies import characters, dictionaries, one_of, text
from main import (
    app, combine_url_and_query, compile_shields_io_url, get_page_count, get_page_hash, redirect_to_github_repository
)
from string import ascii_letters, digits, punctuation
from typing import Any, Dict, Union
from unittest.mock import MagicMock
from urllib.parse import SplitResult, urlsplit
import os
import pytest

# Import environmental variables
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
URL_COUNTAPI = os.getenv("URL_COUNTAPI").rstrip("/")
URL_SHIELDS_IO = os.getenv("URL_SHIELDS_IO").rstrip("/")

# Define allowable characters for testing, i.e. all ASCII letters, digits, punctuation, and a space
CHARACTERS_PAGE = "".join([ascii_letters, digits])
CHARACTERS = "".join([CHARACTERS_PAGE, punctuation]) + " "

# Define hypothesis test strategies
STRATEGY_TEST_INPUT = text(CHARACTERS)
STRATEGY_TEST_INPUT_PAGE = text(CHARACTERS_PAGE, min_size=1)
STRATEGY_TEST_INPUT_QUERY = dictionaries(text(ascii_letters, min_size=1), STRATEGY_TEST_INPUT)


class TestRedirectToGithubRepository:

    def test_flask_redirect_called_correctly(self, patch_flask_redirect: MagicMock) -> None:
        """Test flask.redirect is called in the redirect_to_github_repository function with the correct arguments."""

        # Get the / page of the app
        _ = app.test_client().get("/")

        # Assert flask.redirect is called with the correct arguments
        patch_flask_redirect.assert_called_once_with(GITHUB_REPOSITORY, code=302)

    def test_returns_correctly(self, patch_flask_redirect: MagicMock) -> None:
        """Test the redirect_to_github_repository function returns correctly."""

        # Get the / page of the app
        _ = app.test_client().get("/")

        # Execute the redirect_to_github_repository function
        assert redirect_to_github_repository() == patch_flask_redirect()


# Define test cases for the test_get_page_hash_returns_correctly test
args_test_get_page_hash_returns_correctly = [
    ("foo", "bar", "ff32a30c3af5012ea395827a3e99a13073c3a8d8410a708568ff7e6eb85968fccfebaea039bc21411e9d43fdb9a851b529b"
                   "9960ffea8679199781b8f45ca85e2"),
    ("bar", "foo", "b491a039c51aab2e18c4a7f38401981a078730408bd939df651668cecaf10c1145c55688b28b9f96fd9b966daf66a945131"
                   "aa59c3fed7f321f3fdfc3c47c5b9c")
]


@pytest.mark.parametrize("test_input_page, test_input_hash, test_expected", args_test_get_page_hash_returns_correctly)
def test_get_page_hash_returns_correctly(mocker, test_input_page: str, test_input_hash: str,
                                         test_expected: str) -> None:
    """Test get_page_hash returns the correct value."""

    # Patch the HASH_KEY environment variable
    _ = mocker.patch("main.HASH_KEY", test_input_hash)

    assert get_page_hash(test_input_page) == test_expected


# Define test cases for the combine_url_and_query function
args_test_combine_url_and_query_returns_correctly = [
    ("http://www.google.com", "hello world", "http://www.google.com?hello%20world"),
    ("https://www.google.com", "hello\nworld", "https://www.google.com?hello%0Aworld"),
    (urlsplit("http://www.google.com"), "hello world", "http://www.google.com?hello%20world"),
    (urlsplit("https://www.google.com"), "hello\nworld", "https://www.google.com?hello%0Aworld")
]


@pytest.mark.parametrize("test_input_url, test_input_query, test_expected",
                         args_test_combine_url_and_query_returns_correctly)
def test_combine_url_and_query_returns_corectly(test_input_url: Union[str, SplitResult], test_input_query: str,
                                                test_expected: str) -> None:
    """Test combine_url_and_query returns correctly."""
    assert combine_url_and_query(test_input_url, test_input_query) == test_expected


@given(test_input=STRATEGY_TEST_INPUT)
def test_get_page_count_calls_countapi_correctly(patch_requests_get: MagicMock, test_input: str) -> None:
    """Test get_page_count calls CountAPI correctly."""

    # Call the get_page_count function
    _ = get_page_count(test_input)

    # Assert the requests.get function is called once with the correct argument
    patch_requests_get.assert_called_with(combine_url_and_query(URL_COUNTAPI, test_input))


def mock_requests_get(*args: Any) -> object:
    """Side effect function to mock the requests.get function.

    Based on this StackOverflow answer: https://stackoverflow.com/a/28507806.

    Args:
        *args: A list of arguments, where the first argument is the URL containing the URL_SHIELDS_IO environmental
          variable with an additional URL stub.

    Returns:
        The class MockResponse, which has the attributes json_data, and status_code, and the method json that returns
        json_data. If the URL stub is "", json_data will be None, and status_code will be 404, otherwise they will be
        {"value": 100}, and 200.

    """

    class MockResponse:

        def __init__(self, json_data, status_code):
            """Mock the json_data and status_code attributes, and json method of the requests.get function.

            Args:
                json_data: A mock JSON return.
                status_code: A mock HTTP status code.

            """
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            """Mock the json method of the requests.get function.

            Returns:
                Returns the json_data attribute.

            """
            return self.json_data

    # Define the MockResponse attributes if the URL stub is "" or otherwise
    if args[0] != URL_COUNTAPI:
        return MockResponse({"value": 100}, 200)
    else:
        return MockResponse(None, 404)


@given(test_input=one_of(characters(whitelist_categories="P"), STRATEGY_TEST_INPUT))
def test_get_page_count_returns_correctly_with_working_countapi(patch_requests_get: MagicMock, test_input: str) -> None:
    """Test get_page_count returns the correct counts if the CountAPI is working correctly."""

    # Add a side effect to the requests.get function patch
    patch_requests_get.side_effect = mock_requests_get

    # Call the get_page_count function, and assert the returned value is correct
    if combine_url_and_query(URL_COUNTAPI, test_input) != URL_COUNTAPI:
        assert get_page_count(test_input) == 100
    else:
        assert get_page_count(test_input) is None


def test_get_page_count_returns_correctly_with_failing_countapi(patch_requests_get: MagicMock) -> None:
    """Test get_page_count returns correctly with a failing CountAPI response."""

    # dd a side effect to the requests.get function patch
    patch_requests_get.side_effect = Exception()

    # Call the get_page_count function returns None if request.get raises an exception
    assert get_page_count("test_key") is None


@given(test_input_label=STRATEGY_TEST_INPUT, test_input_message=STRATEGY_TEST_INPUT,
       test_input_color=STRATEGY_TEST_INPUT, test_input_query=STRATEGY_TEST_INPUT_QUERY)
@example(test_input_label="label", test_input_message="message", test_input_color="color", test_input_query={})
def test_compile_shields_io_url_returns_correctly(test_input_label: str, test_input_message: str,
                                                  test_input_color: str, test_input_query: Dict[str, str]) -> None:
    """Test compile_shields_io_url returns the correct string."""

    # Compile the query string, depending if test_input_query is an empty dictionary or not
    if test_input_query:
        compiled_query_string = "&".join(f"{k}={v}" for k, v in test_input_query.items())
    else:
        compiled_query_string = ""

    # Generate the expected URL string
    test_expected = combine_url_and_query(
        f"{URL_SHIELDS_IO}/{test_input_label}-{test_input_message}-{test_input_color}", compiled_query_string
    )

    # Assert that the actual string is the same as the expected on
    assert test_expected == compile_shields_io_url(test_input_label, test_input_message, test_input_color,
                                                   **test_input_query)
