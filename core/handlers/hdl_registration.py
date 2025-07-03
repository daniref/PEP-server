from db import dbAPI as db
from core.utility.utility import *
from core.utility.crc import *
from core.utility.socket import *

MULTICAST_GROUP =   '224.0.0.1'     # Multicast group address for device registration requests
UDP_PORT =          50000           # UDP port for device registration requests

# obtain a logger instance
logger = logging.getLogger(__name__)

def _checkRegReq(data):
    """
    Check if the received data is a registration request.
    :param data: The received data packet.
    :return: True if the data is a registration request, False otherwise.
    """
    if (data[0] == REG_SERV_REQ):
        return True
    else:
        return False

def _handleRegRequest(dataRcv,devAddress):
    """
    Handle the registration request from a device.
    :param dataRcv: The received data packet containing the registration request.
    :param devAddress: The IP address of the device sending the registration request.
    """    
    indexPckt = 0
    vendorNameLength = dataRcv[indexPckt]
    indexPckt = indexPckt+1
    vendorNameByte = bytearray()
    for i in range(vendorNameLength):
        vendorNameByte.append(dataRcv[indexPckt+i])
    indexPckt = indexPckt + vendorNameLength
    
    vendorName = vendorNameByte.decode('ascii')
    logger.debug('Parsing received request, vendorName=%s', vendorName)

    modelNameLength = dataRcv[indexPckt]
    indexPckt = indexPckt+1
    modelNameByte = bytearray()
    for i in range(modelNameLength):
        modelNameByte.append(dataRcv[indexPckt+i])
    indexPckt = indexPckt + modelNameLength
    modelName = modelNameByte.decode('ascii')
    logger.debug('Parsing received request, modelName=%s', modelName)

    if(1==dataRcv[indexPckt]):
        fpgaField=True
    else:
        fpgaField=False
    indexPckt=indexPckt+1
    logger.debug('Parsing received request, fpga=%s', fpgaField)

    macAddressByte = bytearray()
    for i in range(6):
        macAddressByte.append(dataRcv[indexPckt+i])
    macHex = macAddressByte.hex()
    macAddress = ':'.join([macHex[i:i+2] for i in range(0, len(macHex), 2)])
    logger.debug('Parsing received request, macAddress=%s', macAddress)
    
    if (db.DeviceIsRegByMAC(macAddress) == False):
        db.DeviceInsert(macAddress,devAddress,vendorName, modelName, fpgaField, 'available')
        logger.info('Device %s successfull registered!', macAddress)

    else:
        if(db.DeviceIsUsedByMAC(macAddress)):
            db.DeviceUpdateStateByMAC(macAddress,'unavailable')
        else:
            db.DeviceUpdateStateByMAC(macAddress,'available')
        db.DeviceUpdateIPByMAC(macAddress,devAddress)
        logger.info('Device with MAC %s already registered, IP and state updated!', macAddress)

def _sendRegisterResponse(regServiceSocket,address):
    """
    Send a registration response to the device that sent the registration request.
    :param regServiceSocket: The socket used to send the response.
    :param address: The address of the device to send the response to.
    """
    dataToSend = bytearray()
    dataToSend.append(REG_SERV_RES)
    crc16 = CalculateCRC16(dataToSend,crc16poly)
    dataToSend.extend(struct.pack('>H',crc16))    
    SocketSendTo(regServiceSocket,address,dataToSend) 
    
def RegisterDevices():
    """
    Main function to handle device registration requests.
    This function listens for registration requests from devices and processes them.
    """
    logger.info("Active!")
    regServiceSocket = SocketOpenMulticast(MULTICAST_GROUP,UDP_PORT)
    if(None != regServiceSocket):
        while True:
            logger.debug("Waiting for registration request...")
            data, address = SocketRecvFrom(regServiceSocket,BUFFER_SIZE)
            if((CheckMsgIntegrity(data)) and (_checkRegReq(data) == True)): #check if the message is valid and is a registration request
                logger.debug('Received registration request, num bytes: %d', len(data))
                _handleRegRequest(data[1:],address[0])
                _sendRegisterResponse(regServiceSocket,address)
            else:
                logger.info("Unexpected message.")
    else:
        logger.error("Multicast socket not opened")
        return
