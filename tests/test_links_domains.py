import json

import pytest
from mock import Mock, patch

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


@pytest.mark.parametrize('test_input,expected_code', [
    ('', 400),
    ('from={0}'.format(from_date), 400),
    ('to={0}'.format(to_date), 400),
    ('from=ABCD&to={0}'.format(to_date), 400),
    ('from={0}.156&to={1}'.format(from_date, to_date), 400),
    ('from={0}&to={1}'.format(to_date, from_date), 400),
])
def test_visited_domains_incorrect_query(test_client, test_input, expected_code):
    response = test_client.get('/visited_domains?{0}'.format(test_input))
    resp_content = json.loads(response.data)
    assert response.status_code == expected_code
    assert resp_content['status'] == 'error'


@pytest.mark.parametrize('test_input,expected_code', [
    ('from={0}&to={1}'.format(from_date, to_date), 200),
])
def test_visited_domains_correct_structure(
    test_client,
    test_input,
    expected_code,
):
    response = test_client.get('/visited_domains?{0}'.format(test_input))
    resp_content = json.loads(response.data)
    assert response.status_code == expected_code
    assert resp_content['status'] == 'ok'
    assert isinstance(resp_content['domains'], list)


@patch('app.routes.redis')
def test_visited_domains_correct_unique_domains(mock_redis, test_client):
    # Three times we will get the same sites
    mock_redis.lrange.return_value = ['200', '300', '400']
    mock_redis.hget.return_value = '[\"ya.ru\",\"ya.ru\", \"funbox.ru\", \"stackoverflow.com\"]'
    test_input = 'from={0}&to={1}'.format(from_date, to_date)
    response = test_client.get('/visited_domains?{0}'.format(test_input))
    resp_content = json.loads(response.data)
    assert len(resp_content['domains']) == 3
    assert all([domain in resp_content['domains'] for domain in ['ya.ru', 'funbox.ru', 'stackoverflow.com']])


@pytest.mark.parametrize('test_input,expected_code', [
    ("""{"links1": ["ya.ru"]}""", 400),
    ("""{"links": ["ya.ru" "ya.ru"]}""", 400),
    ("""{"links": "ya.ru"}""", 400),
])
def test_visited_links_incorrect_post_format(test_input, expected_code, test_client):
    response = test_client.post('/visited_links', data=test_input)
    resp_content = json.loads(response.data)
    assert response.status_code == expected_code
    assert resp_content['status'] == 'error'


def mock_hset(domains_key_field, datetime_key, domains):
    parsed_domains = json.loads(domains)
    assert len(parsed_domains) == 4
    assert all([domain in parsed_domains for domain in ['ya.ru', 'funbox.ru', 'stackoverflow.com']])


@patch('app.routes.redis')
def test_visited_links_correct_save(mock_redis, test_client):
    expected_code = 200
    mock_redis.hset = Mock(side_effect=mock_hset)
    test_input = """{"links": ["ya.ru", "https://ya.ru?q=123",  "funbox.ru",
        "https://stackoverflow.com/questions/11828270/how-to-exit-the-vim-editor" ]}"""
    response = test_client.post('/visited_links', data=test_input)
    resp_content = json.loads(response.data)
    assert response.status_code == expected_code
    assert resp_content['status'] == 'ok'
