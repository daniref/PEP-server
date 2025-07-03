from core.utility.utility import *
import netifaces
import socket
import struct
import logging
import signal
import sys
import pywifi
from pywifi import const

# INTERFACE_NAME = 'enxd0c0bf2f6edf'
#INTERFACE_NAME = 'wlxc4e90a01bdda'
INTERFACE_NAME = 'wlp0s20f3'

logger = logging.getLogger(__name__) # Set up logger for this module

class SocketManager:
    """
    A class to manage multiple sockets, allowing for their creation, addition, and closure.
    This class is useful for managing resources in network applications where multiple sockets are needed.
    It provides methods to add sockets to a list and close all sockets when they are no longer needed.
    Attributes:
        sockets (list): A list to hold socket objects.
    Methods:
        addSocket(sock): Adds a socket to the list of managed sockets. 
        closeSockets(): Closes all sockets in the list, handling exceptions if a socket is already closed or invalid.
    """
    def __init__(self):
        self.sockets = []

    def addSocket(self, sock):
        self.sockets.append(sock)

    def closeSockets(self):
        for sock in self.sockets:
            try:
                # Check if the socket is still valid before closing
                sock.getsockname()
                sock.close()
                logger.info('Socket %s closed successfully.', sock.getsockname())
            except OSError as e:
                if e.errno == 9:  # Errno 9 è "Bad file descriptor"
                    logger.info('Socket %s already closed or invalid.', sock)
                else:
                    logger.error('Error in closing the Socket %s, %s', sock, e)

socketManager = SocketManager()

def GetIpAddress():
    """
    Retrieves the private IP address of the specified network interface.
    :return: The private IP address as a string, or None if not found.
    """
    try:
        # Obtain the addresses for the specified interface
        addresses = netifaces.ifaddresses(INTERFACE_NAME)
        if netifaces.AF_INET in addresses:
            for address in addresses[netifaces.AF_INET]:
                if 'addr' in address and not address['addr'].startswith('127.'):
                    # Return the first non-loopback address found
                    logger.debug('IP address %s', address['addr'])
                    return address['addr']
        
        logger.error('Private IP address not found for interface %s', INTERFACE_NAME)
        return None  # No valid IP address found
        
    except Exception as e:
        logger.error('Error while fetching IP address for interface %s: %s', INTERFACE_NAME, e)
        return None

def SocketRecvFrom(socket,bufferSize):
    """
    Receives data from a socket.
    :param socket: The socket to receive data from.
    :param bufferSize: The maximum amount of data to be received at once.
    :return: A tuple containing the received data and the address of the sender.
    """
    return socket.recvfrom(bufferSize)

def SocketSendTo(socket,addressToSend,dataToSend):
    """
    Sends data to a specified address using a socket.
    :param socket: The socket to send data through.
    :param addressToSend: The address to which the data should be sent.
    :param dataToSend: The data to be sent.
    """
    logger.debug('Sending a data to %s:', addressToSend)
    socket.sendto(dataToSend,addressToSend)

def SocketOpenMulticast(multicastIP,UDPport):
    """
    Opens a multicast socket for receiving data on a specified multicast IP and UDP port.
    :param multicastIP: The multicast IP address to join.
    :param UDPport: The UDP port to bind the socket to.
    :return: The created socket instance if successful, None otherwise.
    """
    address = ('', UDPport)

    try:
        # Create the socket UDP
        socketInst = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Link the socket to the multicast address and port
        socketInst.bind(address)
        # Add the socket to the multicast group
        socketInst.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(multicastIP) + socket.inet_aton('0.0.0.0'))

        socketManager.addSocket(socketInst)
        return socketInst

    except Exception as e:
        logger.error("Failure in opening multicast socket: %s",e)
        return None

def SocketOpenUnicast(unicastIP, UDPport):
    """
    Opens a unicast socket for receiving data on a specified unicast IP and UDP port.
    :param unicastIP: The unicast IP address to bind the socket to.
    :param UDPport: The UDP port to bind the socket to.
    :return: The created socket instance if successful, None otherwise.
    """
    address = (unicastIP, UDPport)
    try:
        # Create the socket UDP
        socketInst = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Link the socket to the unicast address and port
        logger.debug("UDP socket open at address: %s", address)
        socketInst.bind(address)
        
        socketManager.addSocket(socketInst)
        return socketInst
    
    except Exception as e:
        logger.error("Failure in opening multicast socket: %s",e)
        return None    

def signalHandler(sig, frame):
    """
    Handles the interrupt signal (SIGINT) to gracefully close sockets and exit the program.
    :param sig: The signal number.
    :param frame: The current stack frame (not used here).
    """
    logger.error("Interrupt signal received. Closing sockets...")
    socketManager.closeSockets()
    sys.exit(0)

signal.signal(signal.SIGINT, signalHandler)
