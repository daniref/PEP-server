
from core.utility.utility import *
import struct
from lxml import etree

logger = logging.getLogger(__name__)        # Inizializza il logger per il modulo

def BuildPufsConfigPayload(xmlFile, idpufsConfig):
    """
    Builds the configuration payload for a set of PUFs from an input XML file.

    This function parses an XML configuration file describing one or more PUF instances,
    and encodes the relevant configuration fields into a binary payload. This payload
    is used to configure the device before launching any experiments. The packet header
    is not included and must be added externally.

    Parameters:
        xmlFile (str): Path to the XML file describing the PUF configuration.
        idpufsConfig (int): Unique identifier for the PUF configuration, as stored in the database.

    Returns:
        bytearray: The serialized configuration payload to be sent to the device.
    """

    confPayload = bytearray()

    #Add Header pckt
    xmlParsed = etree.parse(xmlFile)
    rootElem = xmlParsed.getroot()
    logger.debug("The root element is: %s", rootElem.tag)

    #Add pufs config id [2 byte]
    logger.debug("Id Puf Config: %d", idpufsConfig)
    confPayload.extend(struct.pack('>H',idpufsConfig))

    # Add number of PUF instances [1 byte]
    pufInstances = xmlParsed.findall(".//PUFInstance")
    logger.debug("Number of PUF instances: %s", len(pufInstances))
    confPayload.append(len(pufInstances))

    # Add PUF instances configuration
    for puf in pufInstances:
        # Add puf type [1byte]
        pufType = puf.findtext('type')
        logger.debug("Type of PUF instance: %d", int(pufType))
        confPayload.append(int(pufType))
        # Add phy address [4byte]
        phyAddressString = puf.findtext('phyAddress')
        phyAddress = int(phyAddressString,16)
        logger.debug("PhyAddress of PUF instance: %x", phyAddress)
        confPayload.extend(struct.pack('>I',phyAddress))
        # Add ipSize [4byte]
        ipSize = puf.findtext('ipSize')
        logger.debug("Size of PUF IP: %x", int(ipSize,16))
        confPayload.extend(struct.pack('>I',int(ipSize,16)))
        # Add ctrlRegOff [4byte]
        ctrlRegOff = puf.findtext('ctrlRegOff')
        logger.debug("Ctrl Register Offeset: %x", int(ctrlRegOff,16))
        confPayload.extend(struct.pack('>I',int(ctrlRegOff,16)))
        # Add ctrlValue [4byte]
        ctrlValue = puf.findtext('ctrlValue')
        logger.debug("Value of Ctrl Register: %d", int(ctrlValue,16))
        confPayload.extend(struct.pack('>I',int(ctrlValue,16)))        
        # Add readyRegOff [4byte]
        readyRegOff = puf.findtext('readyRegOff')
        logger.debug("ready Register: %x", int(readyRegOff,16))
        confPayload.extend(struct.pack('>I',int(readyRegOff,16)))
        # Add Challenge Size [2byte]
        challengeSize = puf.findtext('chalSize')
        logger.debug("[Commandpacket Service] - Challenge size: %d", int(challengeSize))
        confPayload.extend(struct.pack('>H',int(challengeSize)))
        # Add num challenge register [1byte]
        chalRegOffs = puf.findall('.//chalRegOff/regOff')
        chalRegOffCount = len(chalRegOffs)
        logger.debug("Num challenge registers: %d", int(chalRegOffCount))
        confPayload.append(chalRegOffCount)
        # Add individual challenge registers [4 byte]
        for chalRegOff in chalRegOffs:
            logger.debug("Offset challenge register: %x", int(chalRegOff.text,16))
            confPayload.extend(struct.pack('>I',int(chalRegOff.text,16)))

        # Add Response Size [2byte]
        responseSize = puf.findtext('respSize')
        logger.debug("Response size: %d", int(responseSize))
        confPayload.extend(struct.pack('>H',int(responseSize)))
        # Aggiunge num register [1byte]
        respRegOffs = puf.findall('.//respRegOff/regOff')
        respRegOffCount = len(respRegOffs)
        logger.debug("Num response registers: %d", int(respRegOffCount))
        confPayload.append(respRegOffCount)
        # Add individual response registers [4 byte]
        for respRegOff in respRegOffs:
            logger.debug("Offset response register: %x", int(respRegOff.text,16))
            confPayload.extend(struct.pack('>I',int(respRegOff.text,16)))

        # Add countSize [2byte]
        countSize = puf.findtext('countSize')
        logger.debug("Counters size: %d", int(countSize))
        confPayload.extend(struct.pack('>H',int(countSize)))
        if(int(countSize)!=0):
            # Add num registers count1 [1byte]
            count1RegOffs = puf.findall('.//count1RegOff/regOff')
            count1RegOffsCount = len(count1RegOffs)
            logger.debug("Num count1 registers: %d", int(count1RegOffsCount))
            confPayload.append(count1RegOffsCount)
            # Add individual registers of count1 [4 byte]
            for count1RegOff in count1RegOffs:
                logger.debug("Offset count1 register: %x", int(count1RegOff.text,16))
                confPayload.extend(struct.pack('>I',int(count1RegOff.text,16)))

            # Add num registers count2 [1byte]
            count2RegOffs = puf.findall('.//count2RegOff/regOff')
            count2RegOffsCount = len(count2RegOffs)
            logger.debug("Num count2 registers: %d", int(count2RegOffsCount))
            confPayload.append(count2RegOffsCount)
            # Add individual registers of count2 [4 byte]
            for count2RegOff in count2RegOffs:
                logger.debug("Offset count2 register: %x", int(count2RegOff.text,16))
                confPayload.extend(struct.pack('>I',int(count2RegOff.text,16)))

    return confPayload

def BuildShutdownPayload():
    """
    Builds a shutdown packet payload.

    Even though no payload is required for shutdown operations,
    a minimal payload is returned for compatibility with the
    packet-handling system.

    Returns:
        bytearray: Payload for the shutdown command.
    """
    shutdownPayload = bytearray()
    shutdownPayload.append(DUMMY_PACKET)
    return shutdownPayload

def BuildQueryCommPayload(idCampaign,pufIds,numRep,numByteChallenge,challenge):
    """
    Builds a payload for querying one or more PUF instances on a device.

    The payload can be used to send a challenge to multiple PUFs on the same device,
    specifying the number of repetitions and the length of the challenge.

    Parameters:
        idCampaign (int): Identifier of the experimental campaign.
        pufIds (List[int]): List of PUF IDs to be queried.
        numRep (int): Number of repetitions for each query.
        numByteChallenge (int): Number of bytes that make up the challenge.
        challenge (int): Integer representing the challenge to be issued.

    Returns:
        bytearray: The constructed query payload to be sent to the device.
    """
    pcktQuery = bytearray()
    # Adds id Campaign [2 byte]
    logger.debug("Building Query packet: idCampaign: %d", idCampaign)
    pcktQuery.extend(struct.pack('>H',idCampaign))    
    # Adds Number of challenges [1 byte]
    logger.debug("Building Query packet: number of query: %d", len(pufIds))
    pcktQuery.append(len(pufIds))

    for idPuf in pufIds:
        # Adds id of puf [1 byte]
        logger.debug("Building Query packet: id of puf: %d", idPuf)
        pcktQuery.append(idPuf)
        # Adds num repetion [4 byte]
        logger.debug("Building Query packet: num repetion: %d", numRep)
        pcktQuery.extend(struct.pack('>I',numRep))   
        # Adds Number of bytes of the challenge [1 byte]
        logger.debug("Building Query packet: number of bytes of the challenge: %d", numByteChallenge)
        pcktQuery.append(numByteChallenge)
        # Adds the challenge as a byte array
        logger.debug("Building Query packet: challenge: %d", challenge)
        challengeInByteArray = challenge.to_bytes(numByteChallenge, byteorder='big')
        pcktQuery.extend(challengeInByteArray)
    
    return pcktQuery