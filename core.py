# -*- coding:utf-8 -*-
'''
Created on 2017年5月16日

@author: zhangli
'''
import constants
from abc import abstractmethod, ABCMeta

class InstallTask():
    __metaclass__ = ABCMeta
    
    def __init__(self, host, **kwargs):
        self.host = host
        self.kwargs = kwargs
        
    def execute(self):
        self.process_params()
        self.doExecute()
    
    @abstractmethod
    def doExecute(self):
        pass
    
    def process_params(self):
        self.hosts = self.kwargs["hosts"]
        self.yum = self.kwargs["yum"]
        self.node_type = self.get_node_type()
        
    def get_node_type(self):
        if self.kwargs['controller']['mode'] == 'plain' and self.kwargs['controller']['host'] == self.host['hostname']:
            return constants.NODE_TYPE_CONTROLLER
        else:
            return constants.NODE_TYPE_COMPUTE

class OpenstackServiceInstallTask(InstallTask):
    __metaclass__ = ABCMeta
    
    def __init__(self, host, **kwargs):
        self.host = host
        self.kwargs = kwargs
        
        env = dict()
        env["OS_PROJECT_DOMAIN_NAME"] = "default"
        env["OS_USER_DOMAIN_NAME"] = "default"
        env["OS_PROJECT_NAME"] = "admin"
        env["OS_USERNAME"] = "admin"
        env["OS_PASSWORD"] = "admin"
        env["OS_AUTH_URL"] = "http://%s:35357/v3" % self.get_host(self.kwargs["controller"]["host"])["ip"]
        env["OS_IDENTITY_API_VERSION"] = "3"
        env["OS_IMAGE_API_VERSION"] = "2"
        env["PS1"] = "default"
        self.env = env
    
    def process_params(self):
        InstallTask.process_params(self)
            
    def get_host(self, hostname):
        for host in self.kwargs["hosts"]:
            if host["hostname"] == hostname:
                return host
        return None
            
class Installer():
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        
    def install(self):
        if self.kwargs["controller"]["mode"] == "plain":
            cpi = ControllerPlainInstaller(self.__get_host(self.kwargs["controller"]["host"]), **self.kwargs)
            cpi.install()
            
        for host in self.kwargs["compute"]["hosts"]:
            ci = ComputeInstaller(self.__get_host(host), **self.kwargs)
            ci.install()
    
    def __get_host(self, hostname):
        for host in self.kwargs["hosts"]:
            if host["hostname"] == hostname:
                return host
        return None
        
class ControllerPlainInstaller():
    def __init__(self, host, **kwargs):
        self.host = host
        self.kwargs = kwargs
        self.impl_module = __import__('tasks.%s.%s' % (kwargs['version'], kwargs['os']), fromlist = True)
        
    def install(self):
        self.doTask("OsConfigTask")
        self.doTask("NtpInstallTask")
        self.doTask("MariadbInstallTask")
        self.doTask("RabbitmqInstallTask")
        self.doTask("MemcachedInstallTask")
        self.doTask("OpenstackBasePackagesInstallTask")
        self.doTask("KeystoneInstallTask")
        self.doTask("GlanceInstallTask")
        self.doTask("NovaInstallTask")
        self.doTask("NeutronInstallTask")
        self.doTask("CinderInstallTask")
        self.doTask("HorizonInstallTask")
    
    def doTask(self, task_class):
        task = getattr(self.impl_module, task_class)(self.host, **self.kwargs)
        task.execute()
    
class ComputeInstaller():
    def __init__(self, host, **kwargs):
        self.host = host
        self.kwargs = kwargs
        self.impl_module = __import__('tasks.%s.%s' % (kwargs['version'], kwargs['os']), fromlist = True)
        
    def install(self):
        self.doTask("OsConfigTask")
        self.doTask("NtpInstallTask")
        self.doTask("OpenstackBasePackagesInstallTask")
        self.doTask("ComputeInstallTask")
    
    def doTask(self, task_class):
        task = getattr(self.impl_module, task_class)(self.host, **self.kwargs)
        task.execute()