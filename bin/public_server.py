#coding: UTF-8
__author__ = 'yangchenxing'

import json

import gevent.pywsgi
import redis

import jesgoo

import user_data_utility


class PublicServer:
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
        except PublicServer.Error, e:
            start_response(e.http_status, [('Content-Type', 'text/json')])
            return [json.dumps({
                'success': False,
                'error': e.error_message
            })]

    def _handle(self, method, path, query):
        if method != 'GET':
            raise PublicServer.Error('405 Method Not Allowed', u'不支持的HTTP请求方法')
        if path not in ('/search', '/take'):
            raise PublicServer.Error('400 Bad Request', u'错误的请求路径')
        if path == '/search':
            return self.search(query)
        elif path == '/take':
            return self.take(query)

    def search(self, query):
        for required_param in ('user', 'app'):
            if required_param not in query:
                raise PublicServer.Error('400 Bad Request', u'缺少必要参数')
        try:
            user_id = query['user']
            app_id = query['app']

            modified = False
            user_data = jesgoo.protocol.OfferWallUserData()
            redis_client = redis.Redis(connection_pool=self._redis_pool)
            data = redis_client.get(user_id)
            if data is None:
                return {
                    'success': True,
                    'points': 0
                }
            user_data.ParseFromString(data)
            
            points = 0
            for account in user_data.accounts:
                if account.app_id == app_id:
                    points = account.point
                    break
            modified |= user_data_utility.clean_expired_data(user_data)
            if modified:
                redis_client.set(user_id, user_data.SerializeToString())
            return {
                'success': True,
                'points': points
            }
        except Exception, e:
            raise PublicServer.Error('500 Internal Server Error', e.message)

    def take(self, query):
        for required_param in ('user', 'app'):
            if required_param not in query:
                raise PublicServer.Error('400 Bad Request', u'缺少必要参数')
        try:
            user_id = query['user']
            app_id = query['app']

            modified = False
            user_data = jesgoo.protocol.OfferWallUserData()
            redis_client = redis.Redis(connection_pool=self._redis_pool)
            data = redis_client.get(user_id)
            if data is None:
                return {
                    'success': True,
                    'points': 0
                }
            user_data.ParseFromString(data)

            points = 0
            found = None
            for account in user_data.accounts:
                if account.app_id == app_id:
                    points = account.point
                    found = account
                    break
            if found:
                user_data.remove(found)
                modified = True
            modified |= user_data_utility.clean_expired_data(user_data)
            if modified:
                redis_client.set(user_id, user_data.SerializeToString())
            return {
                'success': True,
                'points': points
            }
        except Exception, e:
            raise PublicServer.Error('500 Internal Server Error', e.message)
