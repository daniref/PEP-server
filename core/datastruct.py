import queue
from core.utility.utility import *
from db import dbAPI as db

logger = logging.getLogger(__name__)        # Inizializza il logger per il modulo

commandsToSend = queue.Queue()              # Coda per gestire tutti i comandi da inviare ai dispositivi
pendingCommandsDict = {}                    # Dizionario per gestire i comandi in attesa di risposta


def EnqueueCommandToSend(retrasmitted,address,type,data):
    """!
    @brief The function enqueues a command to send, by using the
            ip address <address>, the type <type> and the data <data>
            specified as parameters.

    Parameters : 
        @param retrasmitted => If the command is a new command it's value is False, 
                                otherwise it is equal to idCommand to retrasmit.
        @param address => The ip address to which to send the command.
        @param type => The type of the command to send.
        @param data => The data of the command to send.

    """
    command=(retrasmitted,address,type,data)
    commandsToSend.put(command)
    logger.debug("Added a new command to send")

def DequeueCommandToSend():
    """!
    @brief The function returns the first command to send.
    @return Instance of the first command to send.

    """
    return commandsToSend.get(block=False)

def SavePendingCommand(idCommand,address,commType,data,timestamp):
    """!
    @brief [Function's description]

    Parameters : 
        @param idCommand => [description]
        @param address => [description]
        @param commType => [description]
        @param data => [description]
        @param timestamp => [description]

    """
    pendingCommandsDict[idCommand] = (address,commType,data,timestamp)

def EreasePendingCommand(idCommand):
    """!
    @brief The function ereases the pending command having identifier equals to <idCommand>.

    Parameters : 
        @param idCommand => The identifier of the command to erease.

    """
    try:
        pendingCommandsDict.pop(idCommand,None)
    except Exception as e:
        logger.warning("Failure in erasing pending command with id %d: %s",idCommand,e)
        return None

def GetPendingCommandByIdComm(idCommand):
    """!
    @brief The function return the entire pending command having identifier <idCommand>.

    Parameters : 
        @param idCommand => The identifier of the command to be obtained.

    """
    try:
        return pendingCommandsDict[idCommand]
    except Exception as e:
        logger.warning("Failure in getting pending command with id %d: %s",idCommand,e)
        return None

def EreaseAllPendingCommandsOfIdCampaign(idCampaign):
    """!
    @brief Remove all pending commands related to Exp Campaign <idCampaign>.

    Parameters:
        @param idCampaign => Campaign whose pending commands are deleted.
    """
    idDevice = db.CampaignGetDeviceIdByID(idCampaign)
    deviceAddress = db.DeviceGetIPById(idDevice)
    
    keysToRemove = [key for key, value in pendingCommandsDict.items() if value[0] == deviceAddress]
    
    # Rimuovi i comandi pendenti trovati
    for key in keysToRemove:
        del pendingCommandsDict[key]
    
    return len(keysToRemove)

def _FlushCommandsToSend():
    while not commandsToSend.empty():
        commandsToSend.get()

def _FlushPendingCommands():
    pendingCommandsDict.clear()

def FlushDataStructures():
    _FlushCommandsToSend()
    _FlushPendingCommands()
    