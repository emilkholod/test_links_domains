import datetime
import json
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from app import settings
from app.create_app import redis

bp = Blueprint("routes", __name__)


@bp.route('/visited_links', methods=['POST'])
def save_visited_links():
    output = jsonify({"status": "error", "msg": "something went wrong"}), 400
    try:
        body_json = json.loads(request.data)
        check_visited_links_request(body_json)
        save_domains_to_redis(body_json)
        output = jsonify({"status": "ok"})
    except ValueError as e:
        output = jsonify({"status": "error", "msg": str(e)}), 400
    return output


def check_visited_links_request(body_json):
    if 'links' not in body_json.keys():
        raise ValueError("Check key existing 'links' in request")
    if not isinstance(body_json["links"], list):
        raise ValueError("You should send only list of links")


def save_domains_to_redis(body_json):
    parsed_domains = []
    for link in body_json["links"]:
        host = urlparse(link).hostname
        if host is None:
            host = link
        parsed_domains.append(host)
    t = int(datetime.datetime.now().timestamp())
    redis.rpush(settings.DOMAINS_KEY_LIST_IN_REDIS, t)
    redis.hset(settings.DOMAINS_KEY_IN_REDIS, t, json.dumps(parsed_domains))


@bp.route('/visited_domains')
def get_visited_domains():
    output = jsonify({"status": "error", "msg": "something went wrong"}), 400
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        check_get_visited_domains_query_params(from_date, to_date)

        from_date, to_date = int(from_date), int(to_date)
        redis_dates = []
        for t in redis.lrange(settings.DOMAINS_KEY_LIST_IN_REDIS, 0, -1):
            try:
                redis_dates.append(int(t))
            except ValueError:
                pass

        dates_in_between = list(
            filter(lambda x: x >= from_date and x <= to_date, redis_dates))

        unique_domains = set()
        for date_key in dates_in_between:
            unique_domains.update(
                json.loads(redis.hget(settings.DOMAINS_KEY_IN_REDIS,
                                      date_key)))

        output = jsonify({"status": "ok", "domains": list(unique_domains)})
    except ValueError as e:
        output = jsonify({"status": "error", "msg": str(e)}), 400
    return output


def check_get_visited_domains_query_params(from_date, to_date):
    if from_date is None or to_date is None:
        raise ValueError(
            "You should define 'from' and 'to' query params in request")
    try:
        int(from_date), int(to_date)
    except ValueError:
        raise ValueError("You should send data in posix format (integers)")
    if int(from_date) > int(to_date):
        raise ValueError("'from' date should be lower than 'to' date")
