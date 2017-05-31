# -*- coding:utf-8 -*-
'''
Created on 2017年5月16日

@author: zhangli
'''
import logging

class Logger():
    def __init__(self):
        formatter = '%(asctime)s %(filename)s(%(lineno)d) [%(levelname)s] %(message)s'
        level = logging.DEBUG
        logging.basicConfig(level=level,
                        format=formatter,
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        filename='/var/log/openstack-auto-deploy/deploy.log',
                        filemode='w')
        
        console = logging.StreamHandler()
        console.setLevel(level)
        formatter = logging.Formatter(formatter)
        console.setFormatter(formatter)
        logging.getLogger('OPENSTACK_AUTO_DEPLOY').addHandler(console)
    
    def debug(self, message):
        logging.getLogger('OPENSTACK_AUTO_DEPLOY').debug(message)
    
    def info(self, message):
        logging.getLogger('OPENSTACK_AUTO_DEPLOY').info(message)
        
    def error(self, message):
        logging.getLogger('OPENSTACK_AUTO_DEPLOY').error(message)
        
LOGGER = Logger()