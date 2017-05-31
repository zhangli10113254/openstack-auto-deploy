# -*- coding:utf-8 -*-
'''
Created on 2017年5月16日

@author: zhangli
'''

import subprocess, paramiko
from paramiko.ssh_exception import SSHException
from logger import LOGGER

def local_call(command, env = None):
    p = subprocess.Popen(command, shell = True, env = env, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    p.wait()
    if p.returncode == 0:
        LOGGER.debug(p.stdout.read())
        return True
    else:
        LOGGER.error(p.stderr.read())
        return False

def ssh_execute(commands, host = None, timeout = None, environment = None):
    ssh = paramiko.SSHClient()  
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  
    ssh.connect(hostname = host['ip'], port = 22, username = host['username'], password = host['password'])  
    
    for command in commands:
        try:
            LOGGER.debug("*************************** ssh execute(%s): %s" % (host["ip"], command))
            stdin, stdout, stderr = ssh.exec_command (command, environment = environment)
            if stdout.readable():
                log = stdout.read()
                if log:
                    LOGGER.debug(log)
            if stderr.readable():
                log = stderr.read()
                if log:
                    LOGGER.debug(log)
        except SSHException, e:
            print e
            return False
        
    ssh.close()