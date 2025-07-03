from core.handlers.hdl_commands import *
from core.utility import packets as pk
from core import datastruct as ds
from db import dbAPI as db
from core.utility.utility import *
from core import exps as ex

import subprocess

POWER_UP = 'up'
POWER_DOWN = 'down'

SWITCH_ON = 'u'
SWITCH_OFF = 'd'

PORT_DEVICES = 1
PORT_FANS = 2


logger = logging.getLogger(__name__)

def PowerUpBoards():
    """
    The function starts powering up all devices registered on the server.
    return: True The power supply has been correctly switched on.
    return: False The power supply hasn't been correctly switched on.
    """
    logger.info("Powering up boards...")
    ex.ResetThreadStopEvent()
    
    return _SwitchPowerSupply(PORT_DEVICES,SWITCH_ON)

def PowerDownBoards():
    """
    The function starts powering down all devices registered on the server.
    In particular, the functions performs the following steps:
        1. All active experiment threads are stopped, to avoid producing useless commands.
        2. A shutdown command is sent to all reachable devices.
        3. The power supply to the devices is switched off.
    return: True The power supply has been correctly switched off.
    return: False The power supply hasn't been correctly switched off.
    """
    logger.warning("Powering down boards...")
    ex.AbortExperiments()
    time.sleep(COMPLETE_EXEC_COMMAND_TIME)
    ds.FlushDataStructures()
    _ShutdownReachableDevices()
    time.sleep(COMPLETE_SHUTDOWN_DEVICE_TIME) #time necessary to power off petalinux
    db.DeviceSetAllStateUnreachable()
    
    return _SwitchPowerSupply(PORT_DEVICES,SWITCH_OFF)

def PowerUpFans():
    """
    The function starts powering up the fans.
    return: True The power supply has been correctly switched on.
    return: False The power supply hasn't been correctly switched on.
    """
    return _SwitchPowerSupply(PORT_FANS,SWITCH_ON)

def PowerDownFans():
    """
    The function starts powering down the fans.
    return: True The power supply has been correctly switched off.
    return: False The power supply hasn't been correctly switched off.
    """
    return _SwitchPowerSupply(PORT_FANS,SWITCH_OFF)

def _ShutdownReachableDevices():
    """
    The function sends a shutdown command to all reachable devices.
    This is done to ensure that all devices are properly shut down before powering off.
    """
    reachableIPs = db.DeviceGetReachableIP()
    shutdownPayload = pk.BuildShutdownPayload()
    for deviceIP in reachableIPs:
        ds.EnqueueCommandToSend(False,deviceIP,SHUTDOWN_REQ,shutdownPayload)

def _SwitchPowerSupply(port,state):
    """
    The function switches the power supply of the specified port to the desired state (up or down).
    :param port: The port number to switch the power supply for.
    :param state: The desired state of the power supply ('up' or 'down').
    :return: True if the power supply was successfully switched, False otherwise.
    """
    commandToRun = "ykushcmd -"+str(state)+" "+str(port) #always run switching for all downstream ports
    commandArgs = commandToRun.split()

    try:
        subprocess.run(commandArgs,check=True,text=True,capture_output=True)
        logger.info("Power supply of port %d correctly switched in %s", port,state)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Power supply not correctly switched, exception occured %s",e)
        return False
        
    
