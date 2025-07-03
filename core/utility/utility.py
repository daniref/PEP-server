import os
import json
import logging
import time
import pytz
from django.utils import timezone
import re
import struct
import numpy as np
import math

# DEFINE per buffer utilizzati
BUFFER_SIZE =       4096            # Dimensione del buffer per i dati ricevuti

# Headers dei msg scambiati
REG_SERV_REQ =      0xAA            # Richiesta di registrazione sul server da parte del device. */
REG_SERV_RES =      0xA1            # Registrazione sul server avvenuta con successo. */

PUF_CONF_REQ =      0xBB            # Richiesta di configurazione FPGA. */
PUF_CONF_RES =      0xB1            # Esito della richiesta di configurazione FPGA. */

PUF_QURY_REQ =      0xCC            # Richiesta response della PUF. */
PUF_QURY_RES =      0xC1            # Response della PUF. */

SHUTDOWN_REQ =      0xFF            # Request to shutdown devices.      

DUMMY_PACKET =      0x00            # Dummy packet.

RET_OK  =           0             
RET_ERR =           1            


#Waiting time constants in seconds
PENDING_COMMAND_RETRANSMIT_TIME = 360                           #Treshold to establish if a command without response have to be retrasmitted
CHECK_PENDING_COMMANDS_TIME = 30                                #Time period in which server chech if there are commands to retrasmit  
COMPLETE_EXEC_COMMAND_TIME = 2*PENDING_COMMAND_RETRANSMIT_TIME  #Time to wait for complete execution of pending commands before erasing them
COMPLETE_SHUTDOWN_DEVICE_TIME = 40                              #Time to wait after sending a shutdown command, before power off the power supply


relPufsConfigDirectory="configs/pufsConfigurations"     
pufsConfigDirectory = os.path.abspath(relPufsConfigDirectory)

relExpsConfigDirectory="configs/expsConfigurations"          
expsConfigDirectory = os.path.abspath(relExpsConfigDirectory)

genericPufsConfig = pufsConfigDirectory + "/pufsConf_"

genericExpsConfig = expsConfigDirectory + "/expsConf_"

relRunningExpsDirectory="configs/runningExps"
runningExpsDirectory = os.path.abspath(relRunningExpsDirectory)

thresholdDeviceReady = 10
sToWaitDeviceReady = 10

fieldCSVDelimiter=','
lineCSVterminator='\n'

# Funzione per leggere il file JSON e restituire i dati
def ReadJsonFile(filePath):
    with open(filePath, 'r') as file:
        data = json.load(file)
    return data

# Funzione per scrivere i dati aggiornati nel file JSON
def WriteJsonFile(filePath, data):
    with open(filePath, 'w') as file:
        json.dump(data, file, indent=4)


def ExtractNumBytesAsIntegerFromArrayByte(byteArray, numBytes):
    if numBytes > 32 or numBytes < 1:
        raise ValueError("numBytes should be between 1 and 32 inclusive")

    # Estrai i byte specificati dall'array
    byteSegment = byteArray[0:numBytes]

    # Interpreta i byte come un singolo valore intero
    number = int.from_bytes(byteSegment, byteorder='big', signed=False)

    return number

def ExtractFloatFromArrayByte(byteArray):
    # Controlla che il byteArray abbia almeno 4 byte
    if len(byteArray) < 4:
        raise ValueError("Il bytearray deve contenere almeno 4 byte.")

    # Estrai i primi 4 byte
    byteSegment = byteArray[0:4]

    # Interpreta i 4 byte come un valore float (floating-point number)
    floatValue = struct.unpack('f', byteSegment)[0]

    return floatValue
