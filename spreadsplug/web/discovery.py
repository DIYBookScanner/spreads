import logging
import socket
import struct
import threading
from contextlib import closing

DISCOVERY_MESSAGE = "all your scans are belong to us?"
MULTICAST_GROUP = ('224.3.29.71', 10000)
SERVER_ADDRESS = ('', 10000)

logger = logging.getLogger('spreadsplug.web.discovery')


class DiscoveryListener(threading.Thread):
    def __init__(self, server_port):
        super(DiscoveryListener, self).__init__()
        self._server_port = server_port
        self._exit_flag = threading.Event()

    def stop(self):
        self._exit_flag.set()

    def run(self):
        logger.info("Starting discovery listener")
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
            sock.bind(SERVER_ADDRESS)
            # Tell the operating system to add the socket to the multicast
            # group on all interfaces.
            group = socket.inet_aton(MULTICAST_GROUP[0])
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            sock.settimeout(0.2)
            while not self._exit_flag.is_set():
                try:
                    data, address = sock.recvfrom(1024)
                    logger.info("Contact from scanner {0}, acknowledging."
                                .format(address[0]))
                    sock.sendto('ack', address)
                    sock.sendto(bytes(self._server_port), address)
                except socket.timeout:
                    continue


def discover_servers():
    discovered = []
    logger.debug("Discovering servers")
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
        # Set a timeout so the socket does not block indefinitely when trying
        # to receive data.
        sock.settimeout(0.5)

        # Set the time-to-live for messages to 1 so they do not go past the
        # local network segment.
        ttl = struct.pack('b', 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        # Send data to the multicast group
        attempts = 0
        while attempts < 3:
            logger.debug("Sending multicast datagram")
            sock.sendto(DISCOVERY_MESSAGE, MULTICAST_GROUP)
            # Look for responses from all recipients
            last_seen_server = None
            while True:
                try:
                    data, server = sock.recvfrom(16)
                except socket.timeout:
                    break
                else:
                    if data == "ack":
                        logger.debug("Server {0} replied.".format(server[0]))
                        last_seen_server = server[0]
                    elif data.isdigit() and last_seen_server is not None:
                        logger.debug("Server is listening on port {0}"
                                     .format(data))
                        # Set server port
                        discovered.append((last_seen_server, int(data)))
                    else:
                        logger.warning("Received invalid reply from {0}: {1}"
                                       .format(server[0], data))
            if discovered:
                break
            attempts += 1
    return discovered
