#coding: UTF-8
__author__ = 'yangchenxing'

import argparse

import daemon
import gevent
import gevent.monkey
import redis
import yaml

import jesgoo

import public_server
import private_server

gevent.monkey.patch_all()


class Config(object):
    def __init__(self, dict_object):
        config = {name: (value if type(value) is not dict else Config(value))
                  for name, value in dict_object.iteritems()}
        self.__dict__.update(config)

    @staticmethod
    def load(file_path):
        with open(file_path) as config_file:
            return Config(yaml.load(config_file.read()))


def main(args):
    config = Config.load(args.conf)
    redis_pool = redis.ConnectionPool(host=config.redis.host,
                                      port=config.redis.port,
                                      db=config.redis.db)
    external_server = public_server.PublicServer(host=config.public_server.host,
                                                 port=config.public_server.port,
                                                 redis_pool=redis_pool)
    internal_server = private_server.PrivateServer(host=config.private_server.host,
                                                   port=config.private_server.port,
                                                   redis_pool=redis_pool)
    external_server.start()
    internal_server.start()
    gevent.wait((external_server.stop_event, internal_server.stop_event))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='捷酷积分墙积分服务'
    )
    parser.add_argument('--conf',
                        default='conf/offerwall_server.yaml',
                        help='配置文件')
    parser.add_argument('-d', '--daemon',
                        action='store_true',
                        default=False,
                        help='以Daemon方式启动')
    args = parser.parse_args()
    if args.daemon:
        with daemon.DaemonContext():
            main(args)
    else:
        main(args)