import json
from mock import patch, Mock
import pytest

from app.create_app import create_app

from_date = 100
to_date = 1000


@pytest.fixture(scope='module')
def test_client():
    flask_app = create_app()

    # Flask provides a way to test your application by exposing the Werkzeug test Client
    # and handling the context locals for you.
    testing_client = flask_app.test_client()

    # Establish an application context before running the tests.
    ctx = flask_app.app_context()
    ctx.push()

    yield testing_client  # this is where the testing happens!

    ctx.pop()


@pytest.mark.parametrize("test_input,expected", [
    ("", 400),
    (f"from={from_date}", 400),
    (f"to={to_date}", 400),
    (f"from=ABCD&to={to_date}", 400),
    (f"from={from_date}.156&to={to_date}", 400),
    (f"from={to_date}&to={from_date}", 400),
])
def test_visited_domains_incorrect_query(test_client, test_input, expected):
    response = test_client.get('/visited_domains?{0}'.format(test_input))
    content = json.loads(response.data)
    assert response.status_code == expected
    assert content["status"] == "error"


@pytest.mark.parametrize("test_input,expected", [
    (f"from={from_date}&to={to_date}", 200),
])
def test_visited_domains_correct_structure(
        test_client,
        test_input,
        expected,
):
    response = test_client.get('/visited_domains?{0}'.format(test_input))
    content = json.loads(response.data)
    assert response.status_code == expected
    assert content["status"] == "ok"
    assert isinstance(content["domains"], list)


@patch('app.routes.redis')
def test_visited_domains_correct_unique_domains(mock_redis, test_client):
    # Three times we will get the same sites
    mock_redis.lrange.return_value = ["200", "300", "400"]
    mock_redis.hget.return_value = "[\"ya.ru\",\"ya.ru\", \"funbox.ru\", \"stackoverflow.com\"]"
    test_input = f"from={from_date}&to={to_date}"
    response = test_client.get('/visited_domains?{0}'.format(test_input))
    content = json.loads(response.data)
    assert len(content["domains"]) == 3
    assert all([
        domain in content["domains"]
        for domain in ["ya.ru", "funbox.ru", "stackoverflow.com"]
    ])


@pytest.mark.parametrize("test_input,expected", [
    ("""{"links1": []}""", 400),
    ("""{"links": ["ya.ru" "ya.ru"]}""", 400),
    ("""{"links": "ya.ru"}""", 400),
])
def test_visited_links_incorrect_post_format(test_input, expected,
                                             test_client):
    response = test_client.post('/visited_links', data=test_input)
    content = json.loads(response.data)
    assert response.status_code == expected
    assert content["status"] == "error"


@patch('app.routes.redis')
def test_visited_links_correct_save(mock_redis, test_client):
    def mock_hset(key, field, value):
        parsed_domains = json.loads(value)
        print(parsed_domains)
        assert len(parsed_domains) == 4
        assert all([
            domain in parsed_domains
            for domain in ["ya.ru", "funbox.ru", "stackoverflow.com"]
        ])

    mock_redis.hset = Mock(side_effect=mock_hset)
    test_input = """{"links": ["ya.ru", "https://ya.ru?q=123",  "funbox.ru",
        "https://stackoverflow.com/questions/11828270/how-to-exit-the-vim-editor" ]}"""
    response = test_client.post('/visited_links', data=test_input)
    content = json.loads(response.data)
    assert response.status_code == 200
    assert content["status"] == "ok"
