# SSL based command listener class that keeps a persistent connection
#  to the controller to send sensor data

import socket
import ssl
import threading
import time
import errors
import keying

PORT = 4040                                     # port number of controller
CONTROLLER_CN = "controller.machinery.com"      # common name of controller

# a dummy DNS mapping domains to ip addresses
DUMMY_DNS = {"controller.machinery.com": "127.0.0.1",
             "apps.machinery.com": "127.0.0.1",
             "google.com": "172.217.11.23"}


class CommandListener(threading.Thread):
    RECONNECT_INTERVAL = 10     # try reconnecting every 10 seconds on connection loss

    # Constructor
    def __init__(self, sensor):
        super().__init__()
        self.sensor = sensor

    # Function that runs when calling .start() on object
    def run(self):
        # create ssl context
        try:
            context = self.create_ssl_context()
        except Exception as e:
            print("Error creating ssl context: " + str(e))
            print("Server connection will not be attempted")
            return

        while True:     # loop to retry connection to controller
            sock = None
            secure_sock = None

            try:
                # create ssl connection to controller
                sock, secure_sock = self.create_ssl_connection(context)

                # must get "okay" from controller before proceeding
                if self.is_connection_okay(secure_sock) is False:
                    print("Server connection will not be attempted")
                    secure_sock.close()
                    sock.close()
                    return

                while True:     # loop to receive command and return response
                    # receive up to 16 bytes command
                    line = secure_sock.recv(16).decode('utf-8')
                    if len(line) == 0:  # peer disconnected
                        raise errors.GenericError("Connection lost to server backend")

                    # process the command
                    line = line.rstrip()    # strip new line at end
                    print(line)
                    return_msg = self.bulb.run_a_command(line)

                    # return command response
                    print(return_msg)
                    secure_sock.sendall((return_msg + "\n").encode('utf-8'))

            except (ssl.SSLError, socket.error, errors.GenericError) as e:
                print(str(e))
            finally:
                print("Disconnected from server backend")
                if secure_sock is not None:
                    secure_sock.close()
                if sock is not None:
                    sock.close()
                self.bulb.set_connection(False)  # no connection; set gui

    # Create ssl context for use in ssl connection to server
    def create_ssl_context(self):
        # set up TLS1.2 context
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        # both client and server must provide certificates (mutual authentication)
        context.verify_mode = ssl.CERT_REQUIRED
        # load certification authorities
        context.load_verify_locations(keying.CERTIFICATE_AUTHORITY)
        # load client certificate and key
        if self.sensor.sensor_sn == "T79HD20J":
            context.load_cert_chain(certfile=keying.SENSOR_1A2B3C_CERTIFICATE, keyfile=keying.SENSOR_1A2B3C_KEY)
        elif self.sensor.sensor_sn == "H54JU72D":
            context.load_cert_chain(certfile=keying.SENSOR_4D5E6F_CERTIFICATE, keyfile=keying.SENSOR_4D5E6F_KEY)
        elif self.sensor.sensor_sn == "L20YT63C":
            context.load_cert_chain(certfile=keying.SENSOR_7G8H9I_CERTIFICATE, keyfile=keying.SENSOR_7G8H9I_KEY)
        else:
            raise errors.GenericError("Unknown sensor")

        return context

    # Create ssl connection to server backend
    def create_ssl_connection(self, context):
        while True:     # loop to attempt connection until successful
            sock = None
            secure_sock = None
            try:
                # create a secure socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setblocking(True)
                secure_sock = context.wrap_socket(sock, server_side=False, server_hostname=CONTROLLER_CN)
                # connect; call will block if server is available but not answering
                secure_sock.connect((DUMMY_DNS[CONTROLLER_CN], PORT))
                break   # successfully connected; break from loop
            except Exception as e:
                # no connection; wait a bit and retry
                print("Unable to connect to server backend")
                if secure_sock is not None:
                    secure_sock.close()
                if sock is not None:
                    sock.close()
                time.sleep(self.RECONNECT_INTERVAL)
                continue    # retry

        # verify server common name in certificate
        cert = secure_sock.getpeercert()
        if not cert or not self.has_common_name(cert, CONTROLLER_CN):
            raise errors.GenericError("Server common name does not match")

        print("Connected to server backend")
        self.bulb.set_connection(True)  # show on gui

        return sock, secure_sock

    # Check if connection is okay
    def is_connection_okay(self, secure_sock):
        status = secure_sock.recv(128).decode('utf-8')
        if len(status) == 0:  # peer disconnected
            raise errors.GenericError("Connection lost to server backend")

        status = status.rstrip()
        if status != "okay":
            print("Service denied: " + status)
            return False
        else:
            return True

    # Check if a certificate has given common name
    def has_common_name(self, cert, name):
        for fields in cert["subject"]:
            key = fields[0][0]
            value = fields[0][1]
            if key == "commonName":
                if value == name:
                    return True
                else:
                    return False

        return False
