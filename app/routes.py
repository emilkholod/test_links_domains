import contextlib
import datetime
import json
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from app import settings
from app.create_app import redis

bp = Blueprint('routes', __name__)

warning_msg = {'status': 'error', 'msg': 'something went wrong'}


@bp.route('/visited_links', methods=['POST'])
def save_visited_links():
    output = jsonify(warning_msg), 400
    try:
        body_json = json.loads(request.data)
        check_visited_links_request(body_json)
    except ValueError as err:
        output = jsonify({'status': 'error', 'msg': str(err)}), 400
    else:
        save_domains_to_redis(body_json)
        output = jsonify({'status': 'ok'})
    return output


def check_visited_links_request(body_json):
    if 'links' not in body_json.keys():
        raise ValueError("Check key existing 'links' in request")
    if not isinstance(body_json['links'], list):
        raise ValueError('You should send only list of links')


def save_domains_to_redis(body_json):
    parsed_domains = []
    for link in body_json['links']:
        host = urlparse(link).hostname
        if host is None:
            host = link
        parsed_domains.append(host)
    datetime_key = int(datetime.datetime.now().timestamp())
    redis.rpush(settings.DOMAINS_KEY_LIST_IN_REDIS, datetime_key)
    redis.hset(settings.DOMAINS_KEY_IN_REDIS, datetime_key, json.dumps(parsed_domains))


@bp.route('/visited_domains')
def get_visited_domains():
    output = jsonify(warning_msg), 400
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    try:
        check_get_visited_domains_query_params(from_date, to_date)
    except ValueError as err:
        output = jsonify({'status': 'error', 'msg': str(err)}), 400
    else:
        redis_dates = get_redis_dates()
        dates_in_between = [date for date in redis_dates if int(from_date) <= date <= int(to_date)]

        unique_domains = set()
        for date_key in dates_in_between:
            unique_domains.update(json.loads(redis.hget(settings.DOMAINS_KEY_IN_REDIS, date_key)))

        output = jsonify({'status': 'ok', 'domains': list(unique_domains)})

    return output


def get_redis_dates():
    redis_dates = []
    cm = contextlib.suppress(ValueError)
    for str_unix_date in redis.lrange(settings.DOMAINS_KEY_LIST_IN_REDIS, 0, -1):
        with cm:
            redis_dates.append(int(str_unix_date))
    return redis_dates


def check_get_visited_domains_query_params(from_date, to_date):
    if from_date is None or to_date is None:
        raise ValueError("You should define 'from' and 'to' query params in request")
    try:
        from_date, to_date = int(from_date), int(to_date)
    except ValueError:
        raise ValueError('You should send data in posix format (integers)')
    if from_date > to_date:
        raise ValueError("from' date should be lower than 'to' date")
