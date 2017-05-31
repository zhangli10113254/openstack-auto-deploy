# -*- coding:utf-8 -*-
'''
Created on 2017年5月3日

@author: zhangli
'''
from core import InstallTask, OpenstackServiceInstallTask
from mako.template import Template
from logger import LOGGER
import subprocess, utils, constants

class OsConfigTask(InstallTask):
    def __init__(self, host, **kwargs):
        InstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        self.__set_hostname()
        self.__disable_selinux()
        self.__close_firewall()
        self.__config_yum()
        
    def __set_hostname(self):
        LOGGER.debug("=================================== set hostname(%s) ===================================" % self.host["hostname"])
        commands = ["hostnamectl set-hostname %s" % self.host['hostname']]
        commands.append("sed -i '3,$d' /etc/hosts")
        for host in self.hosts:
            commands.append("echo '%s %s' >> /etc/hosts" % (host['ip'], host['hostname']))
        utils.ssh_execute(commands, self.host)
    
    def __disable_selinux(self):
        LOGGER.debug("=================================== disable selinux(%s) ===================================" % self.host["hostname"])
        commands = ["sed -i 's/SELINUX=.*/SELINUX=disabled/' /etc/selinux/config"]
        commands.append("setenforce 0")
        commands.append("getenforce")
        utils.ssh_execute(commands, self.host)
        
    def __close_firewall(self):
        LOGGER.debug("=================================== close firewall(%s) ===================================" % self.host["hostname"])
        commands = ["systemctl disable firewalld"]
        commands.append("systemctl stop firewalld")
        commands.append("systemctl status firewalld")
        utils.ssh_execute(commands, self.host)
            
    def __config_yum(self):
        LOGGER.debug("=================================== config yum(%s) ===================================" % self.host["hostname"])
        commands = ["rm -rf /etc/yum.repos.d/*"]
        utils.ssh_execute(commands, self.host)
        
        commands = list()
        for yum in self.yum:
            commands.append("echo '[%s]' >> /etc/yum.repos.d/openstack.repo" % yum["name"])
            commands.append("echo 'name=%s' >> /etc/yum.repos.d/openstack.repo" % yum["name"])
            commands.append("echo 'baseurl=%s' >> /etc/yum.repos.d/openstack.repo" % yum["url"])
            commands.append("echo 'gpgcheck=0' >> /etc/yum.repos.d/openstack.repo")
            commands.append("echo 'enabled=1' >> /etc/yum.repos.d/openstack.repo")
            commands.append("echo '\n' >> /etc/yum.repos.d/openstack.repo")
            
        commands.append("yum clean all")
        utils.ssh_execute(commands, self.host)
            
class NtpInstallTask(InstallTask):
    def __init__(self, host, **kwargs):
        InstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):          
        LOGGER.debug("=================================== install ntp(%s) ===================================" % self.host["hostname"])
        commands = ["yum install -y chrony"]
        if self.node_type == constants.NODE_TYPE_CONTROLLER:
            commands.append("sed -i '/^allow/d' /etc/chrony.conf")
            commands.append("sed -i '/^#allow/aallow 0.0.0.0/24' /etc/chrony.conf")
        else:
            commands.append("sed -i '/^server /d' /etc/chrony.conf")
            for ntp_server in self.ntp_servers:
                commands.append("sed -i '2 aserver %s iburst' /etc/chrony.conf" % ntp_server)
                
        commands.append("systemctl enable chronyd")
        commands.append("systemctl restart chronyd")
        commands.append("chronyc sources")
        utils.ssh_execute(commands, self.host)
        
    def process_params(self):
        InstallTask.process_params(self)
        if self.kwargs["controller"]["mode"] == "plain":
            self.ntp_servers = [self.kwargs["controller"]["host"]]
            
class MariadbInstallTask(InstallTask):
    def __init__(self, host, **kwargs):
        InstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install mariadb(%s) ===================================" % self.host["hostname"])
        commands = ["yum install -y mariadb mariadb-server python2-PyMySQL"]
        commands.append("sed -i '/^symbolic/acharacter-set-server = utf8' /etc/my.cnf")
        commands.append("sed -i '/^symbolic/acollation-server = utf8_general_ci' /etc/my.cnf")
        commands.append("sed -i '/^symbolic/amax_connections = 4096' /etc/my.cnf")
        commands.append("sed -i '/^symbolic/ainnodb_file_per_table = on' /etc/my.cnf")
        commands.append("sed -i '/^symbolic/adefault-storage_engine = innodb' /etc/my.cnf")
        
        commands.append("systemctl enable mariadb")
        commands.append("systemctl start mariadb")
        
        secure_command = '''(echo ""
            sleep 1
            echo "n"
            sleep 1
            echo "y"
            sleep 1
            echo "y"
            sleep 1
            echo "y"
            sleep 1
            echo "y") | mysql_secure_installation'''
        commands.append(secure_command)
                    
        utils.ssh_execute(commands, self.host)
        
class RabbitmqInstallTask(InstallTask):
    def __init__(self, host, **kwargs):
        InstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install rabbitmq(%s) ===================================" % self.host["hostname"])
        commands = ["yum install -y rabbitmq-server"]      
        commands.append("systemctl enable rabbitmq-server")
        commands.append("systemctl start rabbitmq-server")
        commands.append("rabbitmqctl add_user openstack openstack")
        commands.append("rabbitmqctl set_permissions openstack '.*' '.*' '.*'")
        utils.ssh_execute(commands, self.host)

class MemcachedInstallTask(InstallTask):
    def __init__(self, host, **kwargs):
        InstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install memcached(%s) ===================================" % self.host["hostname"])
        commands = ["yum install -y memcached python-memcached"]
        commands.append("sed -i 's/OPTIONS=.*/OPTIONS=\"-l 0.0.0.0,::1\"/' /etc/sysconfig/memcached")
        commands.append("systemctl enable memcached")
        commands.append("systemctl start memcached")    
        utils.ssh_execute(commands, self.host)
        
class OpenstackBasePackagesInstallTask(InstallTask):
    def __init__(self, host, **kwargs):
        InstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install openstack base packages(%s) ===================================" % self.host["hostname"])
        commands = ["yum install -y python-openstackclient openstack-selinux openstack-utils"]
        utils.ssh_execute(commands, self.host)
        
class KeystoneInstallTask(OpenstackServiceInstallTask):
    def __init__(self, host, **kwargs):
        OpenstackServiceInstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install keystone(%s) ===================================" % self.host["hostname"])
        commands = ["mysql -uroot -e 'create database keystone'"]
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON keystone.* TO \'%s\'@\'localhost\' IDENTIFIED BY \'%s\'"' % ("keystone", "keystone"))
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON keystone.* TO \'%s\'@\'%%\' IDENTIFIED BY \'%s\'"' % ("keystone", "keystone"))  
        
        commands.append("yum install -y openstack-keystone httpd mod_wsgi")
        #commands.append("openstack-config --set /etc/keystone/keystone.conf DEFAULT admin_token 8464d030a1f7ac3f7207")
        commands.append("openstack-config --set /etc/keystone/keystone.conf database connection mysql+pymysql://%s:%s@%s/keystone" % ("keystone", "keystone", self.host["hostname"]))
        commands.append("openstack-config --set /etc/keystone/keystone.conf token provider fernet")
        commands.append("su -s /bin/sh -c 'keystone-manage db_sync' keystone")
        commands.append("keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone")
        commands.append("keystone-manage credential_setup --keystone-user keystone --keystone-group keystone")
        bootstrap = "keystone-manage bootstrap --bootstrap-password %s \
            --bootstrap-admin-url http://%s:35357/v3/ \
            --bootstrap-internal-url http://%s:5000/v3/ \
            --bootstrap-public-url http://%s:5000/v3/ \
            --bootstrap-region-id RegionOne"
        commands.append(bootstrap % ("admin", self.host['ip'], self.host['ip'], self.host['ip']))
        
        #httpd
        commands.append("sed -i 's/#ServerName www.example.com:80/ServerName %s/' /etc/httpd/conf/httpd.conf" % (self.host['hostname']))
        commands.append("ln -s /usr/share/keystone/wsgi-keystone.conf /etc/httpd/conf.d/")
        commands.append("systemctl enable httpd.service")
        commands.append("systemctl start httpd.service")
        utils.ssh_execute(commands, self.host)
        
        utils.local_call("openstack project create --domain default --description 'Service Project' service", env = self.env)
        
class GlanceInstallTask(OpenstackServiceInstallTask):
    def __init__(self, host, **kwargs):
        OpenstackServiceInstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install glance(%s) ===================================" % self.host["hostname"])
        
        utils.local_call("openstack user create --domain default --password glance glance", env = self.env)
        utils.local_call("openstack role add --project service --user glance admin", env = self.env)
        utils.local_call('openstack service create --name glance --description "OpenStack Image" image', env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne image public http://%s:9292" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne image internal http://%s:9292" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne image admin http://%s:9292" % self.host['ip'], env = self.env)    
        
        commands = ["mysql -uroot -e 'create database glance'"]
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON glance.* TO \'%s\'@\'localhost\' IDENTIFIED BY \'%s\'"' % ("glance", "glance"))
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON glance.* TO \'%s\'@\'%%\' IDENTIFIED BY \'%s\'"' % (("glance", "glance")))
        
        commands.append('yum install -y openstack-glance')
        
        commands.append("openstack-config --set /etc/glance/glance-api.conf database connection mysql+pymysql://%s:%s@%s/glance" % ("glance", "glance", self.host['ip']))
        commands.append("openstack-config --set /etc/glance/glance-api.conf keystone_authtoken auth_uri http://%s:5000" % (self.host["ip"]))
        commands.append("openstack-config --set /etc/glance/glance-api.conf keystone_authtoken auth_url http://%s:35357" % (self.host["ip"]))
        commands.append("openstack-config --set /etc/glance/glance-api.conf keystone_authtoken memcached_servers %s:11211" % (self.host["ip"]))
        commands.append("openstack-config --set /etc/glance/glance-api.conf keystone_authtoken auth_type password")
        commands.append("openstack-config --set /etc/glance/glance-api.conf keystone_authtoken project_domain_name default")
        commands.append("openstack-config --set /etc/glance/glance-api.conf keystone_authtoken user_domain_name default")
        commands.append("openstack-config --set /etc/glance/glance-api.conf keystone_authtoken project_name service")
        commands.append("openstack-config --set /etc/glance/glance-api.conf keystone_authtoken username glance")
        commands.append("openstack-config --set /etc/glance/glance-api.conf keystone_authtoken password glance")
        commands.append("openstack-config --set /etc/glance/glance-api.conf paste_deploy flavor keystone")
        commands.append("openstack-config --set /etc/glance/glance-api.conf glance_store stores file,http")
        commands.append("openstack-config --set /etc/glance/glance-api.conf glance_store default_store file")
        commands.append("openstack-config --set /etc/glance/glance-api.conf glance_store filesystem_store_datadir /var/lib/glance/images")
        
        commands.append("openstack-config --set /etc/glance/glance-registry.conf database connection mysql+pymysql://%s:%s@%s/glance" % ("glance", "glance", self.host['ip']))
        commands.append("openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken auth_uri http://%s:5000" % (self.host["ip"]))
        commands.append("openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken auth_url http://%s:35357" % (self.host["ip"]))
        commands.append("openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken memcached_servers %s:11211" % (self.host["ip"]))
        commands.append("openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken auth_type password")
        commands.append("openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken project_domain_name default")
        commands.append("openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken user_domain_name default")
        commands.append("openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken project_name service")
        commands.append("openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken username glance")
        commands.append("openstack-config --set /etc/glance/glance-registry.conf keystone_authtoken password glance")
        commands.append("openstack-config --set /etc/glance/glance-registry.conf paste_deploy flavor keystone")
        
        commands.append('su -s /bin/sh -c "glance-manage db_sync" glance')
        
        commands.append("systemctl enable openstack-glance-api.service openstack-glance-registry.service")
        commands.append("systemctl start openstack-glance-api.service openstack-glance-registry.service")
        utils.ssh_execute(commands, self.host)

class NovaInstallTask(OpenstackServiceInstallTask):
    def __init__(self, host, **kwargs):
        OpenstackServiceInstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install Nova(%s) ===================================" % self.host["hostname"])
        
        utils.local_call("openstack user create --domain default --password nova nova", env = self.env)
        utils.local_call("openstack role add --project service --user nova admin", env = self.env)
        utils.local_call('openstack service create --name nova --description "OpenStack Compute" compute', env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne compute public http://%s:8774/v2.1" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne compute internal http://%s:8774/v2.1" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne compute admin http://%s:8774/v2.1" % self.host['ip'], env = self.env)
        
        utils.local_call("openstack user create --domain default --password placement placement", env = self.env)
        utils.local_call("openstack role add --project service --user placement admin", env = self.env)
        utils.local_call('openstack service create --name placement --description "Placement API" placement', env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne placement public http://%s:8778/nova-placement-api" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne placement internal http://%s:8778/nova-placement-api" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne placement admin http://%s:8778/nova-placement-api" % self.host['ip'], env = self.env)
        
        commands = ["mysql -uroot -e 'create database nova'"]
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON nova.* TO \'%s\'@\'localhost\' IDENTIFIED BY \'%s\'"' % ("nova", "nova"))
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON nova.* TO \'%s\'@\'%%\' IDENTIFIED BY \'%s\'"' % ("nova", "nova"))
        commands.append("mysql -uroot -e 'create database nova_api'")
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON nova_api.* TO \'%s\'@\'localhost\' IDENTIFIED BY \'%s\'"' % ("nova", "nova"))
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON nova_api.* TO \'%s\'@\'%%\' IDENTIFIED BY \'%s\'"' % ("nova", "nova"))
        commands.append("mysql -uroot -e 'create database nova_cell0'")
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON nova_cell0.* TO \'%s\'@\'localhost\' IDENTIFIED BY \'%s\'"' % ("nova", "nova"))
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON nova_cell0.* TO \'%s\'@\'%%\' IDENTIFIED BY \'%s\'"' % ("nova", "nova"))
        
        commands.append('yum install -y openstack-nova-api openstack-nova-conductor openstack-nova-console openstack-nova-novncproxy openstack-nova-scheduler openstack-nova-placement-api')
        commands.append("openstack-config --set /etc/nova/nova.conf DEFAULT enabled_apis osapi_compute,metadata")
        commands.append("openstack-config --set /etc/nova/nova.conf DEFAULT my_ip %s" % self.host['ip'])
        commands.append("openstack-config --set /etc/nova/nova.conf DEFAULT transport_url rabbit://%s:%s@%s" % ("openstack", "openstack", self.host['ip']))
        commands.append("openstack-config --set /etc/nova/nova.conf database connection mysql+pymysql://%s:%s@%s/nova" % ("nova", "nova", self.host['ip']))
        commands.append("openstack-config --set /etc/nova/nova.conf api_database connection mysql+pymysql://%s:%s@%s/nova_api" % ("nova", "nova", self.host['ip']))
        
        commands.append("openstack-config --set /etc/nova/nova.conf api auth_strategy keystone")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_uri http://%s:5000" % (self.host['ip']))
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_url http://%s:35357" % (self.host['ip']))
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken memcached_servers %s:11211" % (self.host['ip']))
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_type password")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken project_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken user_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken project_name service")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken username nova")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken password nova")
        
        commands.append("openstack-config --set /etc/nova/nova.conf DEFAULT use_neutron True")
        commands.append("openstack-config --set /etc/nova/nova.conf DEFAULT firewall_driver nova.virt.firewall.NoopFirewallDriver")
        
        commands.append("openstack-config --set /etc/nova/nova.conf vnc enabled True")
        commands.append("openstack-config --set /etc/nova/nova.conf vnc vncserver_listen $my_ip")
        commands.append("openstack-config --set /etc/nova/nova.conf vnc vncserver_proxyclient_address $my_ip")
        
        commands.append("openstack-config --set /etc/nova/nova.conf glance api_servers http://%s:9292" % self.host['ip'])
        
        commands.append("openstack-config --set /etc/nova/nova.conf oslo_cuncurrency lock_path /var/lib/nova/tmp")
        
        commands.append("openstack-config --set /etc/nova/nova.conf placement os_region_name RegionOne")
        commands.append("openstack-config --set /etc/nova/nova.conf placement project_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf placement project_name service")
        commands.append("openstack-config --set /etc/nova/nova.conf placement user_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf placement auth_type password")
        commands.append("openstack-config --set /etc/nova/nova.conf placement auth_url http://%s:35357" % (self.host['ip']))
        commands.append("openstack-config --set /etc/nova/nova.conf placement username placement")
        commands.append("openstack-config --set /etc/nova/nova.conf placement password placement")
        
        commands.append("openstack-config --set /etc/nova/nova.conf neutron url http://%s:9696" % self.host['ip'])
        commands.append("openstack-config --set /etc/nova/nova.conf neutron auth_url http://%s:35357" % self.host['ip'])
        commands.append("openstack-config --set /etc/nova/nova.conf neutron auth_type password")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron project_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron user_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron region_name RegionOne")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron project_name service")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron username neutron")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron password neutron")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron service_metadata_proxy true")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron metadata_proxy_shared_secret openstack")
        
        commands.append("openstack-config --set /etc/nova/nova.conf cinder os_region_name RegionOne")
        
        commands.append('su -s /bin/sh -c "nova-manage api_db sync" nova')
        commands.append('su -s /bin/sh -c "nova-manage cell_v2 map_cell0" nova')
        commands.append('su -s /bin/sh -c "nova-manage cell_v2 create_cell --name=cell1 --verbose" nova 109e1d4b-536a-40d0-83c6-5f121b82b650')
        commands.append('su -s /bin/sh -c "nova-manage db sync" nova')
        
        commands.append('systemctl enable openstack-nova-api openstack-nova-consoleauth  openstack-nova-scheduler openstack-nova-conductor openstack-nova-novncproxy')
        commands.append('systemctl start openstack-nova-api openstack-nova-consoleauth  openstack-nova-scheduler openstack-nova-conductor openstack-nova-novncproxy')
        
        utils.ssh_execute(commands, self.host)
        
class NeutronInstallTask(OpenstackServiceInstallTask):
    def __init__(self, host, **kwargs):
        OpenstackServiceInstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install Neutron(%s) ===================================" % self.host["hostname"])
        
        utils.local_call("openstack user create --domain default --password neutron neutron", env = self.env)
        utils.local_call("openstack role add --project service --user neutron admin", env = self.env)
        utils.local_call('openstack service create --name neutron --description "OpenStack Networking" network', env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne network public http://%s:9696" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne network internal http://%s:9696" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne network admin http://%s:9696" % self.host['ip'], env = self.env)
        
        commands = ["mysql -uroot -e 'create database neutron'"]
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON neutron.* TO \'%s\'@\'localhost\' IDENTIFIED BY \'%s\'"' % ("neutron", "neutron"))
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON neutron.* TO \'%s\'@\'%%\' IDENTIFIED BY \'%s\'"' % ("neutron", "neutron"))
        
        commands.append("yum install -y openstack-neutron openstack-neutron-ml2 openstack-neutron-openvswitch ebtables")
        
        commands.append("openstack-config --set /etc/neutron/neutron.conf database connection mysql+pymysql://%s:%s@%s/neutron" % ("neutron", "neutron", self.host['ip']))
        
        commands.append("openstack-config --set /etc/neutron/neutron.conf DEFAULT core_plugin ml2")
        commands.append("openstack-config --set /etc/neutron/neutron.conf DEFAULT service_plugins router")
        commands.append("openstack-config --set /etc/neutron/neutron.conf DEFAULT allow_overlapping_ips true")
        
        commands.append("openstack-config --set /etc/neutron/neutron.conf DEFAULT notify_nova_on_port_status_changes true")
        commands.append("openstack-config --set /etc/neutron/neutron.conf DEFAULT notify_nova_on_port_data_changess true")
        
        commands.append("openstack-config --set /etc/neutron/neutron.conf DEFAULT transport_url rabbit://%s:%s@%s" % ("openstack", "openstack", self.host['ip']))
        commands.append("openstack-config --set /etc/neutron/neutron.conf DEFAULT auth_strategy keystone")
        
        commands.append("openstack-config --set /etc/neutron/neutron.conf keystone_authtoken auth_uri http://%s:5000" % (self.host['ip']))
        commands.append("openstack-config --set /etc/neutron/neutron.conf keystone_authtoken auth_url http://%s:35357" % (self.host['ip']))
        commands.append("openstack-config --set /etc/neutron/neutron.conf keystone_authtoken memcached_servers %s:11211" % (self.host['ip']))
        commands.append("openstack-config --set /etc/neutron/neutron.conf keystone_authtoken auth_type password")
        commands.append("openstack-config --set /etc/neutron/neutron.conf keystone_authtoken project_domain_name default")
        commands.append("openstack-config --set /etc/neutron/neutron.conf keystone_authtoken user_domain_name default")
        commands.append("openstack-config --set /etc/neutron/neutron.conf keystone_authtoken project_name service")
        commands.append("openstack-config --set /etc/neutron/neutron.conf keystone_authtoken username neutron")
        commands.append("openstack-config --set /etc/neutron/neutron.conf keystone_authtoken password neutron")
        
        commands.append("openstack-config --set /etc/neutron/neutron.conf nova auth_url http://%s:35357" % (self.host['ip']))
        commands.append("openstack-config --set /etc/neutron/neutron.conf nova auth_type password")
        commands.append("openstack-config --set /etc/neutron/neutron.conf nova project_domain_name default")
        commands.append("openstack-config --set /etc/neutron/neutron.conf nova user_domain_name default")
        commands.append("openstack-config --set /etc/neutron/neutron.conf nova region_name RegionOne")
        commands.append("openstack-config --set /etc/neutron/neutron.conf nova project_name service")
        commands.append("openstack-config --set /etc/neutron/neutron.conf nova username nova")
        commands.append("openstack-config --set /etc/neutron/neutron.conf nova password nova")
        
        commands.append("openstack-config --set /etc/neutron/neutron.conf oslo_cuncurrency lock_path /var/lib/nova/tmp")
        
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/ml2_conf.ini ml2 type_drivers flat,vlan,vxlan")
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/ml2_conf.ini ml2 tenant_network_types vxlan")
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/ml2_conf.ini ml2 mechanism_drivers openvswitch,l2population")
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/ml2_conf.ini ml2 extension_drivers port_security")
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/ml2_conf.ini ml2_type_flat flat_networks provider")
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/ml2_conf.ini ml2_type_vlan network_vlan_ranges external:1:4090")
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/ml2_conf.ini ml2_type_vxlan vni_ranges 1:1000")
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/ml2_conf.ini securitygroup enable_ipset true")
        
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/openvswitch_agent.ini securitygroup firewall_driver iptables_hybrid")
        
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/openvswitch_agent.ini agent tunnel_types vxlan")
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/openvswitch_agent.ini agent l2_population True")
        
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/openvswitch_agent.ini ovs bridge_mappings provider:br-provider")
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/openvswitch_agent.ini ovs local_ip %s" % self.host['ip'])
        
        commands.append("openstack-config --set /etc/neutron/dhcp_agent.ini DEFAULT interface_driver openvswitch")
        commands.append("openstack-config --set /etc/neutron/dhcp_agent.ini DEFAULT dhcp_driver neutron.agent.linux.dhcp.Dnsmasq")
        commands.append("openstack-config --set /etc/neutron/dhcp_agent.ini DEFAULT enable_isolated_metadata true")
        
        commands.append("openstack-config --set /etc/neutron/l3_agent.ini DEFAULT interface_driver openvswitch")
        commands.append("openstack-config --set /etc/neutron/l3_agent.ini DEFAULT external_network_bridge")
        
        commands.append("openstack-config --set /etc/neutron/metadata_agent.ini DEFAULT nova_metadata_ip %s" % self.host['ip'])
        commands.append("openstack-config --set /etc/neutron/metadata_agent.ini DEFAULT metadata_proxy_shared_secret openstack")
        
        commands.append("ln -s /etc/neutron/plugins/ml2/ml2_conf.ini /etc/neutron/plugin.ini")
        commands.append('su -s /bin/sh -c "neutron-db-manage --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini upgrade head" neutron')
        
        commands.append("systemctl enable openvswitch.service")
        commands.append("systemctl start openvswitch.service")
        
        commands.append("ovs-vsctl add-br br-provider")
        
        commands.append("systemctl enable neutron-server.service neutron-openvswitch-agent.service neutron-dhcp-agent.service neutron-metadata-agent.service neutron-l3-agent.service")
        commands.append("systemctl start neutron-server.service neutron-openvswitch-agent.service neutron-dhcp-agent.service neutron-metadata-agent.service neutron-l3-agent.service")        
        
        utils.ssh_execute(commands, self.host)
        
class CinderInstallTask(OpenstackServiceInstallTask):
    def __init__(self, host, **kwargs):
        OpenstackServiceInstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install Cinder(%s) ===================================" % self.host["hostname"])
        
        utils.local_call("openstack user create --domain default --password cinder cinder", env = self.env)
        utils.local_call("openstack role add --project service --user cinder admin", env = self.env)
        utils.local_call('openstack service create --name cinder --description "OpenStack Volumn" volume', env = self.env)
        utils.local_call('openstack service create --name cinderv2 --description "OpenStack VolumnV2" volumev2', env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne volume public http://%s:8776/v1/%%\(tenant_id\)s" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne volume internal http://%s:8776/v1/%%\(tenant_id\)s" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne volume admin http://%s:8776/v1/%%\(tenant_id\)s" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne volumev2 public http://%s:8776/v2/%%\(tenant_id\)s" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne volumev2 internal http://%s:8776/v2/%%\(tenant_id\)s" % self.host['ip'], env = self.env)
        utils.local_call("openstack endpoint create --region RegionOne volumev2 admin http://%s:8776/v2/%%\(tenant_id\)s" % self.host['ip'], env = self.env)
        
        commands = ["mysql -uroot -e 'create database cinder'"]
                
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON cinder.* TO \'%s\'@\'localhost\' IDENTIFIED BY \'%s\'"' % ("cinder", "cinder"))
        commands.append('mysql -uroot -e "GRANT ALL PRIVILEGES ON cinder.* TO \'%s\'@\'%%\' IDENTIFIED BY \'%s\'"' % ("cinder", "cinder"))
        
        commands.append('yum install -y openstack-cinder')
        
        commands.append("openstack-config --set /etc/cinder/cinder.conf database connection mysql+pymysql://%s:%s@%s/cinder" % ("cinder", "cinder", self.host["ip"]))
        
        commands.append("openstack-config --set /etc/cinder/cinder.conf DEFAULT transport_url rabbit://%s:%s@%s" % ("openstack", "openstack", self.host["ip"]))
        commands.append("openstack-config --set /etc/cinder/cinder.conf DEFAULT auth_strategy keystone")
        
        commands.append("openstack-config --set /etc/cinder/cinder.conf keystone_authtoken auth_uri http://%s:5000" % (self.host["ip"]))
        commands.append("openstack-config --set /etc/cinder/cinder.conf keystone_authtoken auth_url http://%s:35357" % (self.host["ip"]))
        commands.append("openstack-config --set /etc/cinder/cinder.conf keystone_authtoken memcached_servers %s:11211" % (self.host["ip"]))
        commands.append("openstack-config --set /etc/cinder/cinder.conf keystone_authtoken auth_type password")
        commands.append("openstack-config --set /etc/cinder/cinder.conf keystone_authtoken project_domain_name default")
        commands.append("openstack-config --set /etc/cinder/cinder.conf keystone_authtoken user_domain_name default")
        commands.append("openstack-config --set /etc/cinder/cinder.conf keystone_authtoken project_name service")
        commands.append("openstack-config --set /etc/cinder/cinder.conf keystone_authtoken username cinder")
        commands.append("openstack-config --set /etc/cinder/cinder.conf keystone_authtoken password cinder")
        
        commands.append("openstack-config --set /etc/cinder/cinder.conf DEFAULT my_ip %s" % self.host['ip'])
        commands.append("openstack-config --set /etc/cinder/cinder.conf oslo_concurrency lock_path /var/lib/cinder/tmp")
        
        commands.append('su -s /bin/sh -c "cinder-manage db sync" cinder')
        
        if self.cinder_property['storage_type'] == 'lvm':
            commands.append("yum install -y targetcli python-keystone lvm2")
            
            commands.append("systemctl enable lvm2-lvmetad.service")
            commands.append("systemctl start lvm2-lvmetad.service")
        
            commands.append("pvcreate %s" % self.cinder_property['storage_property']['device'])
            commands.append("vgcreate cinder-volumes %s" % self.cinder_property['storage_property']['device'])
            
            commands.append("openstack-config --set /etc/cinder/cinder.conf lvm volume_driver cinder.volume.drivers.lvm.LVMVolumeDriver")
            commands.append("openstack-config --set /etc/cinder/cinder.conf lvm volume_group cinder-volumes")
            commands.append("openstack-config --set /etc/cinder/cinder.conf lvm iscsi_protocol iscsi")
            commands.append("openstack-config --set /etc/cinder/cinder.conf lvm iscsi_helper lioadm")
            
            commands.append("openstack-config --set /etc/cinder/cinder.conf DEFAULT enabled_backends lvm")
            
            commands.append("openstack-config --set /etc/cinder/cinder.conf DEFAULT glance_api_servers http://%s:9292" % self.host["ip"])
            
        commands.append("systemctl enable openstack-cinder-api.service openstack-cinder-scheduler openstack-cinder-volume.service target.service")
        commands.append("systemctl start openstack-cinder-api.service openstack-cinder-scheduler openstack-cinder-volume.service target.service")        
        utils.ssh_execute(commands, self.host)
        
    def process_params(self):
        OpenstackServiceInstallTask.process_params(self)
        self.cinder_property = self.kwargs["controller"]["service_properties"]["cinder"]
        
class HorizonInstallTask(OpenstackServiceInstallTask):
    def __init__(self, host, **kwargs):
        OpenstackServiceInstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install Cinder(%s) ===================================" % self.host["hostname"])
    
        data = dict()
        data['CONTROLLER_HOST'] = self.host['ip']
        data['MEMCACHED_HOST'] = self.host['ip']
        
        commands = ["yum install -y openstack-dashboard"]
        utils.ssh_execute(commands, self.host)
        
        t = Template(filename = "%s/local_settings.tpl" % constants.TEMPLATE_DIR)
        with open("%s/local_settings" % constants.TEMP_DIR, "w") as f:
            f.write(t.render(**data))
            
        utils.local_call('sshpass -p %s scp %s/local_settings root@%s:/etc/openstack-dashboard/local_settings' % (self.host['password'], constants.TEMP_DIR, self.host['ip']), env = self.env)
        
        commands = ["systemctl restart httpd"]
        utils.ssh_execute(commands, self.host)
        
    def process_params(self):
        OpenstackServiceInstallTask.process_params(self)
        
class ComputeInstallTask(OpenstackServiceInstallTask):
    def __init__(self, host, **kwargs):
        OpenstackServiceInstallTask.__init__(self, host, **kwargs)
        
    def doExecute(self):
        LOGGER.debug("=================================== install Compute(%s) ===================================" % self.host["hostname"])
        
        commands = ["yum install -y openstack-nova-compute"]
        commands.append("openstack-config --set /etc/nova/nova.conf DEFAULT enabled_apis osapi_compute,metadata")
        commands.append("openstack-config --set /etc/nova/nova.conf DEFAULT my_ip %s" % self.host['ip'])
        commands.append("openstack-config --set /etc/nova/nova.conf DEFAULT transport_url rabbit://%s:%s@%s" % ("openstack", "openstack", self.controller_ip))
        
        commands.append("openstack-config --set /etc/nova/nova.conf api auth_strategy keystone")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_uri http://%s:5000" % (self.controller_ip))
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_url http://%s:35357" % (self.controller_ip))
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken memcached_servers %s:11211" % (self.controller_ip))
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken auth_type password")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken project_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken user_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken project_name service")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken username nova")
        commands.append("openstack-config --set /etc/nova/nova.conf keystone_authtoken password nova")
        
        commands.append("openstack-config --set /etc/nova/nova.conf DEFAULT use_neutron True")
        commands.append("openstack-config --set /etc/nova/nova.conf DEFAULT firewall_driver nova.virt.firewall.NoopFirewallDriver")
        
        commands.append("openstack-config --set /etc/nova/nova.conf vnc enabled True")
        commands.append("openstack-config --set /etc/nova/nova.conf vnc vncserver_listen $my_ip")
        commands.append("openstack-config --set /etc/nova/nova.conf vnc vncserver_proxyclient_address $my_ip")
        commands.append("openstack-config --set /etc/nova/nova.conf novncproxy_base_url http://%s:6080/vnc_auto.html" % self.controller_ip)
        
        commands.append("openstack-config --set /etc/nova/nova.conf glance api_servers http://%s:9292" % self.controller_ip)
        commands.append("openstack-config --set /etc/nova/nova.conf oslo_cuncurrency lock_path /var/lib/nova/tmp")
        
        commands.append("openstack-config --set /etc/nova/nova.conf placement os_region_name RegionOne")
        commands.append("openstack-config --set /etc/nova/nova.conf placement project_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf placement project_name service")
        commands.append("openstack-config --set /etc/nova/nova.conf placement user_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf placement auth_type password")
        commands.append("openstack-config --set /etc/nova/nova.conf placement auth_url http://%s:35357" % (self.controller_ip))
        commands.append("openstack-config --set /etc/nova/nova.conf placement username placement")
        commands.append("openstack-config --set /etc/nova/nova.conf placement password placement")
        
        commands.append("openstack-config --set /etc/nova/nova.conf libvirt virt_type %s" % self.virt_type)
        
        commands.append("systemctl enable libvirtd.service openstack-nova-compute.service")
        commands.append("systemctl start libvirtd.service openstack-nova-compute.service")
        
        #neutron
        commands.append("yum install -y openstack-neutron-openvswitch ebtables ipset")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron url http://%s:9696" % self.controller_ip)
        commands.append("openstack-config --set /etc/nova/nova.conf neutron auth_url http://%s:35357/v3" % self.controller_ip)
        commands.append("openstack-config --set /etc/nova/nova.conf neutron auth_type v3password")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron project_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron user_domain_name default")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron region_name RegionOne")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron project_name service")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron username neutron")
        commands.append("openstack-config --set /etc/nova/nova.conf neutron password neutron")
        
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/openvswitch_agent.ini ovs local_ip %s" % self.host['ip'])
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/openvswitch_agent.ini agent tunnel_types vxlan")
        commands.append("openstack-config --set /etc/neutron/plugins/ml2/openvswitch_agent.ini agent l2_population True")
        
        commands.append("systemctl enable openvswitch.service neutron-openvswitch-agent.service")
        commands.append("systemctl start openvswitch.service neutron-openvswitch-agent.service")
        utils.ssh_execute(commands, self.host)
        
    def process_params(self):
        OpenstackServiceInstallTask.process_params(self)
        self.controller_host = self.kwargs["controller"]["host"]
        for host in self.kwargs["hosts"]:
            if host["hostname"] == self.controller_host:
                self.controller_ip = host["ip"]
                
        self.virt_type = self.kwargs["compute"]["virt_type"]