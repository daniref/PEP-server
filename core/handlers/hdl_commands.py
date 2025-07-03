from django.shortcuts import render

import json
import queue
import time as tm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import concurrent.futures
import atexit
import signal

from db import dbAPI as db
from core.utility.crc import *
from core.utility.socket import *
from core.power.power import *
from core.utility.packets import *
from core.conf.conf import *
from core import datastruct as ds

logger = logging.getLogger(__name__)        # Initialize the logger
COMMAND_UDP_PORT =           44000          # Port for commands
shutdownEvent = threading.Event()
exec = concurrent.futures.ThreadPoolExecutor()

def HandlerCommands():
    """
    Initializes and manages threads for handling command socket communication.
    This function creates a unicast socket using the specified IP address and port,
    and starts three daemon threads to handle different aspects of communication:
    - Sending messages (`HandleTxMsgs`)
    - Receiving messages (`HandleRxMsgs`)
    - Processing pending commands (`HandlePendingCommand`)
    If the socket cannot be created, the function exits without performing any operations.
    Returns:
        None
    """

    commandSocket = SocketOpenUnicast(GetIpAddress(),COMMAND_UDP_PORT)
    if(None != commandSocket):
        # Create threads for sending, receiving, and handling pending commands
        sendThread = threading.Thread(target=HandleTxMsgs,args=(commandSocket,))
        recvThread = threading.Thread(target=HandleRxMsgs,args=(commandSocket,))
        pendThread = threading.Thread(target=HandlePendingCommand,args=(commandSocket,))

        sendThread.daemon = True
        sendThread.start()

        recvThread.daemon = True
        recvThread.start()

        pendThread.daemon = True
        pendThread.start()
    else:
        return

def HandlePendingCommand(socket):
    """
    Handles pending commands by checking if any commands need to be retransmitted.
    This function runs in a loop, checking the `pendingCommandsDict` for commands that
    have not been acknowledged within a specified time frame (`PENDING_COMMAND_RETRANSMIT_TIME`).
    If a command is found that needs to be retransmitted, it is sent again using the
    `ds.EnqueueCommandToSend` method, and the command is removed from the pending list.
    The function also maintains a connection to the SQL database by calling `db.DeviceKeepAliveDBConnection`.
    Args:
        socket: The socket used for sending commands.
    Returns:
        None
    """
    logger.info("HandlePendingCommand: Activated!")
    while not shutdownEvent.is_set():
        currentTime = time.time()
        for idCommand, (address, commType, data, timestamp) in list(ds.pendingCommandsDict.items()):
            if currentTime - timestamp > PENDING_COMMAND_RETRANSMIT_TIME:
                logger.info("Retrasmission of command %d to %s of type %d", idCommand, address,commType)
                ds.EreasePendingCommand(idCommand)
                ds.EnqueueCommandToSend(idCommand,address,commType,data)  # Enqueue the command to be sent again
        logger.info("Waiting for %d seconds", CHECK_PENDING_COMMANDS_TIME)
        db.DeviceKeepAliveDBConnection() #only to maintain connection with sql DB
        time.sleep(CHECK_PENDING_COMMANDS_TIME)

    logger.warning("HandlePendingCommand: Terminated!")

def HandleRxMsgs(commandsSocket):
    """
    Handles incoming messages from the command socket.
    This function runs in a loop, waiting for messages to be received from the socket.
    When a message is received, it checks the integrity of the message using `CheckMsgIntegrity`.
    If the message is valid, it extracts the command ID and checks the operation result using `_CheckOpResult`.
    Depending on the command type, it processes the message accordingly:
    - For `PUF_CONF_RES`, it updates the device state to 'ready'.
    - For `PUF_QURY_RES`, it saves the CRPs (Challenge-Response Pairs) using `_SaveCRPsByIdCommand`.
    If the command type is not recognized, it logs an error.
    If the message is corrupted or too short, it logs a warning.
    Args:
        commandsSocket: The socket used for receiving commands.
    Returns:
        None
    """
    logger.info("HandleRxMsgs: Activated!")
    # receive data from the socket
    while not shutdownEvent.is_set():
        logger.debug("Waiting for command responses...")
        rcvdData, address = SocketRecvFrom(commandsSocket,BUFFER_SIZE)
        if len(rcvdData)>= 4:
            if(CheckMsgIntegrity(rcvdData)): #check integrity of the received message
                logger.debug('The received message is valid and its size is %d', len(rcvdData))
                rcvdDataString = ' '.join(f'{byte:02X}' for byte in rcvdData)
                logger.debug("Received message: %s", rcvdDataString)
                idCommand = struct.unpack('>I', rcvdData[1:5])[0]
                if(_CheckOpResult(rcvdData[5])):
                    logger.debug('The operation of command %d was successfull!', idCommand)
                    commandType = rcvdData[0]
                    if commandType == PUF_CONF_RES:
                        logger.debug('Command type: pufs config response received, command id %d!', idCommand)
                        idDev = db.DeviceGetIdByAddress(address[0])
                        db.DeviceSetStateById(idDev,'ready')
                    elif commandType == PUF_QURY_RES:
                        logger.debug('Command type: puf response received, command id %d!', idCommand)
                        _SaveCRPsByIdCommand(idCommand,rcvdData[6:])
                    else:
                        logger.error('Command type: not recognized, command id %d!', idCommand)
                else:
                    logger.debug('The operation of command %d failed!', idCommand)
                ds.EreasePendingCommand(idCommand)
            else:
                logger.warning("Received message corrupted!")
        else:
            logger.warning("Received message too short!")
    
    logger.warning("HandleRxMsgs: Terminated!")

def HandleTxMsgs(commandsSocket):
    """
    Handles the transmission of messages through the command socket.
    This function runs in a loop, waiting for commands to be dequeued from the `ds.DequeueCommandToSend` queue.
    When a command is dequeued, it constructs a message to be sent, including the command type, command ID, and data.
    It calculates the CRC16 checksum for the message and appends it to the data before sending.
    The message is sent to the specified address using the `SocketSendTo` function.
    If the command is not a retransmission, it increments the command ID for the next command.
    The function continues to run until the `shutdownEvent` is set, at which point it terminates.
    Args:
        commandsSocket: The socket used for sending commands.
    Returns:
        None
    """
    logger.info("HandleTxMsgs: Activated!")
    idCommand = 0
    while not shutdownEvent.is_set():
        # logger.info("Waiting for a command to process")
        try:
            retrasmitted,address,commType,data = ds.DequeueCommandToSend()
            logger.debug("New command dequeued")
            dataToSend = bytearray()
            dataToSend.append(commType)
            if retrasmitted == False:
                commandId=idCommand
            else:
                commandId=retrasmitted
            dataToSend.extend(struct.pack('>I', commandId))  # '>H' code for big-endian unsigned short
            dataToSend.extend(data)
            crc16=CalculateCRC16(dataToSend,crc16poly)
            dataToSend.extend(struct.pack('>H',crc16))
            addressToSend=(address,COMMAND_UDP_PORT)
            SocketSendTo(commandsSocket,addressToSend,dataToSend)
            logger.info("Sent command %d to %s ",commandId,address)
            timestamp = time.time()
            if commType is not SHUTDOWN_REQ:
                ds.SavePendingCommand(commandId,address,commType,data,timestamp)  # saves all data to repeat the entire command
            if retrasmitted == False:
                idCommand = (idCommand + 1) % (2**32) # restart from zero each 4 bytes
        except queue.Empty:
            continue
    logger.warning("HandleTxMsgs: Terminated!")

def _CheckOpResult(result):
    """
    Checks the result of an operation.
    This function checks if the result of an operation is successful (RET_OK).
    It logs the result and returns True if the operation was successful, otherwise it returns False.
    Args:
        result: The result of the operation to check.
    Returns:
        bool: True if the operation was successful, False otherwise.   
    """
    logger.debug('The result of operation is %d', result)
    if (result == RET_OK):
        return True
    else:
        return False

def _SaveCRPsByIdCommand(idCommand,rcvdData):
    """
    Saves the Challenge-Response Pairs (CRPs) for a given command ID.
    This function retrieves the pending command by its ID, extracts the campaign ID and other details,
    and processes the received data to save the CRPs in the database.
    It checks the integrity of the received data against the sent data, extracts relevant information,
    and logs the details of the campaign, voltage, temperature, and each CRP.
    Args:
        idCommand: The ID of the command for which to save the CRPs.
        rcvdData: The received data containing the CRPs.
    Returns:
        bool: True if the CRPs were saved successfully, False otherwise.
    """
    result = ds.GetPendingCommandByIdComm(idCommand)
    if(None != result):
        (address,commType,sntData,timestamp) = result
    else:
        logger.warning("The CRP has not been saved!")
        return False
    ds.EreasePendingCommand(idCommand)
    indexSentData=0
    indexRcvdData=0
    idCampaign = struct.unpack('>H', sntData[indexSentData:indexSentData+2])[0]
    idCampaignRcvd = struct.unpack('>H', rcvdData[indexRcvdData:indexRcvdData+2])[0]
    if(idCampaignRcvd!=idCampaign):
        return False
    indexRcvdData+=2
    indexSentData+=2
    logger.debug('Campaign id %d', idCampaign)

    campaign = db.CampaignGetCampaignByID(idCampaign)

    numCRPs=sntData[indexSentData]
    if(rcvdData[indexRcvdData]!=numCRPs):
        return False
    indexRcvdData+=1
    indexSentData+=1
    logger.debug('PUF Query resp - Num CRPs to save %d', numCRPs)

    voltage = ExtractFloatFromArrayByte(rcvdData[-6:])
    logger.debug('PUF Query resp - Voltage value: %f', voltage)

    temperature = ExtractFloatFromArrayByte(rcvdData[-10:])
    logger.debug('PUF Query resp - Temperature value: %f', temperature)

    for numQuery in range(numCRPs):

        logger.debug('PUF Query resp - Parsing response  #%d', numQuery)

        idPuf = sntData[indexSentData]
        if(rcvdData[indexRcvdData]!=idPuf):
            return False
        indexRcvdData+=1
        indexSentData+=1
        logger.debug('PUF Query resp - Info on query to puf with id %d', idPuf)

        numRep = struct.unpack('>I',sntData[indexSentData:indexSentData+4])[0]
        numRepRcvd = struct.unpack('>I',rcvdData[indexRcvdData:indexRcvdData+4])[0]
        if(numRepRcvd!=numRep):
            return False
        indexRcvdData+=4
        indexSentData+=4        
        logger.debug('PUF Query resp - Number of Query repetion %d', numRepRcvd)

        numChalBytes = sntData[indexSentData]
        indexSentData+=1
        logger.debug('PUF Query resp - Num bytes of challenge: %d', numChalBytes)

        challengeBytes = sntData[indexSentData:indexSentData+numChalBytes]
        challengeHexString = str(''.join(format(byte, '02x').upper() for byte in challengeBytes))
        indexSentData+=numChalBytes
        logger.debug('PUF Query resp - Challenge sent: %s', challengeHexString)

        numRespBytes = rcvdData[indexRcvdData]
        indexRcvdData+=1
        logger.debug('PUF Query resp - Num bytes of response: %d', numRespBytes)

        responseBytes = rcvdData[indexRcvdData:indexRcvdData+numRespBytes]
        responseHexString = str(''.join(format(byte, '02x').upper() for byte in responseBytes))
        indexRcvdData+=numRespBytes
        logger.debug('PUF Query resp - Response received: %s', responseHexString)

        if (XMLPufsConfigAreThereCountReg(idCampaign,idPuf)):
            numCountBytes = rcvdData[indexRcvdData]
            indexRcvdData+=1
            counter1Bytes = rcvdData[indexRcvdData:indexRcvdData+numCountBytes]
            counter1HexString = str(''.join(format(byte, '02x').upper() for byte in counter1Bytes))
            indexRcvdData+=numCountBytes

            counter2Bytes = rcvdData[indexRcvdData:indexRcvdData+numCountBytes]
            counter2HexString = str(''.join(format(byte, '02x').upper() for byte in counter2Bytes))
            indexRcvdData+=numCountBytes
        else:
            counter1HexString = None
            counter2HexString = None

        logger.debug('PUF Query resp - Counter 1 value: %s', counter1HexString)
        logger.debug('PUF Query resp - Counter 2 value: %s', counter2HexString)

        db.CRPInsert(campaign,idPuf,numRep,challengeHexString,responseHexString,counter1HexString,counter2HexString,temperature,voltage)
    return True

def shutdown(sig,frame):
    """
    Handles the shutdown signal by setting the shutdown event and cleaning up resources.
    This function is registered to handle the SIGINT signal (typically triggered by Ctrl+C).
    It sets the `shutdownEvent` to signal that the threads should stop running.
    It then shuts down the `ThreadPoolExecutor`, updates the device states in the database to 'unreachable',
    and exits the program.
    Args:
        sig: The signal number that triggered the shutdown.
        frame: The current stack frame (not used in this function). 
    Returns:
        None
    """
    shutdownEvent.set()
    exec.shutdown()
    db.DeviceSetAllStateUnreachable()
    sys.exit(0)

# atexit.register(shutdown)
signal.signal(signal.SIGINT, shutdown)
