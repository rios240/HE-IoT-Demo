# Controller that accepts ssl connections from sensors
#   The backend maintains a queue for each connected bulb,
#   to which the frontend writes commands
#   The backend forwards commands to the frontend from a
#   bulb's queue and returns the response to the frontend
#   A bulb is a client of the backend

from sqlalchemy.exc import SQLAlchemyError
import threading
import socket
import ssl
import time
import queue
import os
import database
import errors

CERTIFICATE_AUTHORITY = "trust_store/machineryca.crt"
CONTROLLER_CERTIFICATE = "trust_store/controller.crt"
CONTROLLER_KEY = "trust_store/controller_keypair.pem"

# SENSOR_COM_TIMEOUT = 10   # maximum number of seconds to wait for bulb response


class Controller(threading.Thread):
    HOST = "0.0.0.0"    # can connect from any ip
    PORT = 4040         # port number of backend

    # Constructor
    def __init__(self):
        super().__init__()
        self.relay_queues = {}  # dictionary for bulb command queues

    # Function that runs when calling .start() on object
    def run(self):

        # create a secure server socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.HOST, self.PORT))
        server_socket.listen(32)    # 32 maximum connections

        # create ssl context
        try:
            context = self.create_ssl_context()
            secure_server_sock = context.wrap_socket(server_socket, server_side=True)
        except Exception as e:
            print("[backend]\tError creating ssl server socket: " + str(e))
            print("[backend]\tTERMINATED!")
            return

        while True:     # loop to accept new connections and start handlers
            client = None
            address = None
            try:
                # wait for connection
                client, address = secure_server_sock.accept()
                print("[backend]\tConnection from " + address[0] + ":" + str(address[1]))

                # verify client mentioned in certificate is known
                cert = client.getpeercert()
                bulb_id_from_cert = self.verify_common_name(cert)
                if not cert or bulb_id_from_cert is None:
                    client.sendall("Unknown client".encode("utf-8"))
                    raise errors.GenericError("Unknown client")

                # do not allow duplicate connections
                if bulb_id_from_cert in self.relay_queues:
                    client.sendall("Client already exists".encode("utf-8"))
                    raise errors.GenericError("Duplicate connection from " + bulb_id_from_cert)

                # all okay; start handling client
                client.sendall("okay".encode("utf-8"))
                threading.Thread(target=self.handle_client, args=[client, bulb_id_from_cert]).start()

            except (errors.GenericError, ssl.SSLError, socket.error) as e:
                print("[backend]\t" + str(e))
                if client is not None:
                    print("[backend]\tDisconnected from " + address[0] + ":" + str(address[1]))
                    client.close()

    # Handle connection from a client (bulb)
    def handle_client(self, client, bulb_id):
        # create a queue to receive commands for this bulb
        client_queue = queue.SimpleQueue()

        # store reference to the queue
        self.relay_queues[bulb_id] = client_queue

        print("[backend]\tConnected to " + bulb_id)

        try:
            while True:     # loop to read a command and send response
                # try reading a command from queue
                try:
                    (command, w_fd) = client_queue.get(block=False)
                except queue.Empty:
                    command = None  # no command in queue
                    w_fd = None
                    time.sleep(0.1)

                # clear any data in incoming buffer
                client.setblocking(False)
                while True:     # loop until no data in buffer
                    try:
                        drop_data = client.recv(1)  # SSLWantReadError exception when no data
                    except ssl.SSLWantReadError:
                        break   # simply break out of while loop
                    if len(drop_data) == 0:
                        raise errors.GenericError("Connection lost to " + bulb_id)

                # process command if available
                if command is not None:
                    # send command to bulb
                    client.setblocking(True)
                    client.sendall(command.encode('utf-8'))

                    # receive response
                    client.settimeout(BULB_COM_TIMEOUT)
                    try:
                        status = client.recv(128).decode('utf-8')
                        if len(status) == 0:
                            raise errors.GenericError("Connection lost to " + bulb_id)
                    except socket.timeout:  # response taking too long; forget it!
                        print("[backend]\t" + bulb_id + " timeout while waiting for response")
                        status = "timeout"

                    # forward response to frontend
                    try:
                        os.write(w_fd, status.rstrip().encode("utf-8"))
                    except Exception as e:
                        print("[backend]\tIgnoring error while returning response to frontend: " + str(e))
                        pass
        except (ssl.SSLError, socket.error, errors.GenericError) as e:
            print("[backend]\t" + str(e))
        finally:
            self.relay_queues.pop(bulb_id)     # remove the queue for this bulb
            print("[backend]\tDisconnected from " + bulb_id)
            client.close()

    # Create ssl context for use in ssl connection to client (bulb)
    def create_ssl_context(self):
        # set up TLS1.2 context
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        # both client and server must provide certificates (mutual authentication)
        context.verify_mode = ssl.CERT_REQUIRED
        # load certification authorities
        context.load_verify_locations(CERTIFICATE_AUTHORITY)
        # load server certificate and key
        context.load_cert_chain(certfile=CONTROLLER_CERTIFICATE, keyfile=CONTROLLER_KEY)

        return context

    # Extract common name from certificate and return bulb id if known
    def verify_common_name(self, cert):
        # search common name field in certificate and attempt match
        for fields in cert["subject"]:
            key = fields[0][0]
            value = fields[0][1]
            if key == "commonName":
                # see if bulb id is in database
                bulb_id = value.split(".", 1)[0]
                try:
                    if database.Bulb.query.filter_by(id=bulb_id).first() is None:
                        return None
                    else:
                        return bulb_id
                except SQLAlchemyError as e:
                    print("[backend]\t" + str(e))
                    database.db.session.rollback()
                    return None

        # common name not in certificate
        return None

    # Add a command to the relay queue of a bulb
    def add_to_relay_queue(self, bulb_id, command, fd):
        try:
            # put command and write descriptor in queue for bulb_id
            # write descriptor is used to write the command response
            self.relay_queues[bulb_id].put((command, fd))
        except (KeyError, queue.Full):  # bulb queue not present or full
            return False

        return True
