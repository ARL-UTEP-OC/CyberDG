from guacapy import Guacamole
import requests
import os
import binascii
import codecs
import sys


class RDPManager():
    def __init__(self, username=None, password=None):
        self.addr = os.environ.get('GUAC_ADDR')
        self.path = os.environ.get('GUAC_PATH')
        self.guacd_hostname = os.environ.get('GUACD_HOSTNAME')
        self.guacd_port = os.environ.get('GUACD_PORT')
        self.guacConn = self.generate_conn(username, password)
        self.vbox_ip = os.environ.get('VBOX_IP')
        self.vbox_port = os.environ.get('VBOX_PORT')

    def generate_conn(self, username=None, password=None):
        if not username:
            username = 'guacadmin'
        if not password:
            password = 'guacadmin'
        guacConn = Guacamole(self.addr,
                             username=username,
                             password=password,
                             url_path=self.path,
                             method='http')
        return guacConn

    def add_user(self, username, password):
        print("creating user", username)
        try:
            payload = self.generate_user_payload(username, password)
            user = self.guacConn.add_user(payload)
            self.grant_permission(username, 'CREATE_CONNECTION')
            return user
        except Exception as e:
            print(e)
            print("Error, could not create user")

    def switch_user(self, username, password):
        self.guacConn = self.generate_conn(username, password)

    def get_user(self, username):
        print("getting user", username)
        try:
            return self.guacConn.get_user(username)
        except:
            print('Error, could not get user')

    def get_users(self):
        try:
            return self.guacConn.get_users()
        except:
            print('could not get all users')

    def delete_user(self, username):
        print('deleting user', username)
        try:
            return self.guacConn.delete_user(username)
        except requests.exceptions.HTTPError:
            #print('Error, could not delete user')
            return False

    def delete_all_users(self):
        users = self.get_users()
        try:
            for u in users:
                if users[u].get('username') is 'guacadmin':
                    pass
                self.delete_user(users[u].get('username'))
            print('All users have been deleted')
        except:
            print('cannot delete user')

    #def logout(self, user):
    def add_connection(self,
                       name="",
                       username="",
                       password="",
                       hostname="",
                       port="",
                       max_connections=2,
                       max_connections_per_user=2):
        print('adding connection', name)
        try:
            payload = self.generate_rdp_payload(name,
                                                username,
                                                password,
                                                hostname,
                                                port,
                                                max_connections,
                                                max_connections_per_user)
            return self.guacConn.add_connection(payload)
        except:
            print("Error, could not add connection")

    def get_connection(self, connection_id):
        print('getting connection', connection_id)
        try:
            return self.guacConn.get_connection_full(connection_id)
        except:
            print('Error, could not get connection')


    def get_connection_id(self, machine_id):
        conn = self.guacConn.get_connection_by_name(machine_id)
        return conn.get('identifier')


    def get_connection_link(self, connection_id):
        byt = bytes(str(connection_id), 'utf-8')
        hx = binascii.hexlify(byt)
        if len(hx) == 4:
            conn_id = hx
        else:
            conn_id = b''.join([b'00', hx])
            print(conn_id)
        con_and_auth = b'006300706F737467726573716C'
        link_hex = b''.join([conn_id + con_and_auth])
        link = codecs.encode(codecs.decode(link_hex, 'hex'), 'base64').decode()
        return link[:-1]

    def delete_connection(self, connection_id):
        print('deleting connection', connection_id)
        try:
            return self.guacConn.delete_connection(connection_id)
        except:
            print("Error, could not delete connection")

    def get_connections(self):
        try:
            return self.guacConn.get_connections()
        except:
            print('Error, could not get connections')

## DELETE ALL CONNECTIONS 
    def delete_all_connections(self):
        connections = self.get_connections()
        try:
            for c in connections.get('childConnections'):
                self.delete_connection(c.get('identifier'))
            print('All connections in guac_db have been deleted')
        except:
            print('Could not delete connections from guac_db' )

    def grant_permission(self, username, permission):
        print('granting permission to', username)
        try:
            payload = [{"op": "add",
                        "path": "/systemPermissions",
                        "value": permission}]
            return self.guacConn.grant_permission(username, payload)
        except:
            print("Error, could not grant permission")

    def generate_user_payload(self, username, password):
        payload = {
            "username": username,
            "password": password,
            "attributes":
                {"disabled": "",
                 "expired": "",
                 "access-window-start": "",
                 "access-window-end": "",
                 "valid-from": "",
                 "valid-until": "",
                 "timezone": 0}
        }
        return payload

    def generate_rdp_payload(self,
                             name,
                             username,
                             password,
                             hostname,
                             port,
                             max_connections,
                             max_connections_per_user):
        if not hostname:
            hostname = self.vbox_ip
        if not port:
            port = self.vbox_port
        payload = {
            "name": name,
            "identifier": "",
            "parentIdentifier": "ROOT",
            "protocol": "rdp",
            "attributes": {
                "max-connections": max_connections,
                "max-connections-per-user": max_connections_per_user,
                "guacd-hostname": self.guacd_hostname,
                "guacd-port": self.guacd_port
            },
            "activeConnections": 0,
            "parameters": {
                "username": username,
                "password": password,
                "disable-audio": "",
                "server-layout": "",
                "domain": "",
                "hostname": hostname,
                "enable-font-smoothing": "",
                "security": "rdp",
                "port": port,
                "disable-auth": "",
                "ignore-cert": "",
                "console": "",
                "width": "",
                "height": "",
                "dpi": "",
                "color-depth": "",
                "console-audio": "",
                "enable-printing": "",
                "enable-drive": "",
                "create-drive-path": "",
                "enable-wallpaper": "",
                "enable-theming": "",
                "enable-full-window-drag": "",
                "enable-desktop-composition": "",
                "enable-menu-animations": "",
                "preconnection-id": "",
                "enable-sftp": "",
                "sftp-port": ""
            }
        }
        return payload


def runCommand(arg):
    rdpmgr = RDPManager()
    if arg == 'rmUsers':
        rdpmgr.delete_all_users()
    if arg == 'rmConnections':
        rdpmgr.delete_all_connections()
    else:
        print("Please enter rmUsers or rmConnections")


if __name__ == "__main__":
    cmd = sys.argv[1]
    runCommand(cmd)
