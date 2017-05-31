# -*- coding:utf-8 -*-
'''
Created on 2017年4月25日

@author: zhangli
'''
import json
from core import Installer

if __name__ == '__main__':
    test_file_name = '/home/zhangli/workspace/eclipse/openstack-auto-deploy/deploy_cfg.json'
    with open(test_file_name) as fp:
        params = json.load(fp)
        
    installer = Installer(**params)
    installer.install()
