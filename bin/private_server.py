#coding: UTF-8
__author__ = 'yangchenxing'

import json
import time

import gevent.pywsgi
import redis

import jesgoo

import user_data_utility


class PrivateServer:
    class Error(Exception):
        def __init__(self, http_status, error_message):
            Exception.__init__(self, error_message)
            self._http_status = http_status
            self._error_message = error_message

        @property
        def http_status(self):
            return self._http_status

        @property
        def error_message(self):
            return self._error_message

    def __init__(self, host, port, redis_pool, **kwargs):
        self._redis_pool = redis_pool
        self._wsgi_server = gevent.pywsgi.WSGIServer((host, port), self._handle, **kwargs)

    def start(self):
        self._wsgi_server.start()

    def stop(self):
        self._wsgi_server.stop()

    @property
    def stop_event(self):
        return getattr(self._wsgi_server, '_stop_event')

    def handle(self, env, start_response):
        method = env['REQUEST_METHOD']
        path = env['PATH_INFO']
        query = dict(param.split('=', 1) for param in env['QUERY_STRING'].split('&') if '=' in param)
        try:
            return self._handle(method, path, query)
        except PrivateServer.Error, e:
            start_response(e.http_status, [('Content-Type', 'text/json')])
            return [json.dumps({
                'success': False,
                'error': e.error_message
            })]

    def _handle(self, method, path, query):
        if method != 'GET':
            raise PrivateServer.Error('405 Method Not Allowed', u'不支持的HTTP请求方法')
        if path not in ('/charge'):
            raise PrivateServer.Error('400 Bad Request', u'错误的请求路径')
        if path == '/charge':
            return self.charge(query)

    def charge(self, query):
        for required_param in ('user', 'app', 'job', 'points'):
            if required_param not in query:
                raise PrivateServer.Error('400 Bad Request', u'缺少必要参数')
        try:
            user_id = query['user']
            app_id = query['app']
            job_id = query['job']
            points = int(query['point'])

            user_data = jesgoo.protocol.OfferWallUserData()
            redis_client = redis.Redis(connection_pool=self._redis_pool)
            data = redis_client.get(user_id)
            if data is not None:
                user_data.ParseFromString(data)
            else:
                user_data.user_id = user_id

            job = filter(lambda x: x.id == job_id, user_data.done_jobs)
            if not job:
                return {
                    'success': False,
                    'error': u'任务不可重复完成'
                }
            job = user_data.done_jobs.add()
            job.id = job_id
            job.timestamp = int(time.time())
            account = filter(lambda x: x.app_id == app_id, user_data.accounts)
            if account:
                account = account[0]
            else:
                account = user_data.accounts.add()
                account.app_id = app_id
                account.points = 0
            account.points += points
            user_data_utility.clean_expired_data(user_data)
            redis_client.set(user_id, user_data.SerializeToString())
            return {
                'success': True,
            }
        except Exception, e:
            raise PrivateServer.Error('500 Internal Server Error', e.message)