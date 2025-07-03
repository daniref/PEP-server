from db import dbAPI as db
from core.utility.utility import *
from core.utility.packets import *
import core.datastruct as ds
from core.conf import conf as cf

import random
import re
import threading

logger = logging.getLogger(__name__)        # Inizializza il logger per il modulo
stopExpThread = threading.Event()           # Event used to stop all exps threads

def RunChalRangeExp(snapshotFile):
    """!
    @brief The function implements the thread logic used by the server 
            to perform experiments of type 'range'.
    @details Starting with a snapshot file in which the information useful 
            for running the experiments is stored, the function initializes 
            its local variables and then starts the loop in which it factually 
            queues the query commands to be sent to the device. 
            It should be noted that at each iteration the snapshot file is updated and 
            it is checked to see if the experiment interrupting event has been set.

    Parameters : 
        @param snapshotFile => The file used as snapshot to save the progress of the experiment.
        @param stopExpThread => Interrupting event.

    """
    try:
        data = ReadJsonFile(snapshotFile)
        idCampaign = _GetPufCampIdsFromSnapshot(snapshotFile)
        pufIds = data['puf_ids']
        logger.info(f"Initialization of a new thread associated to a range-type experiment. IdCampaign={idCampaign}, pufIds={pufIds}")

        challengeBitsWidth = int(data['challengeBitsWidth'])
        step = int(data['step'])
        numExps = int(data['numExps'])
        expInterperiod_m = int(data['expInterperiod_m'])
        queriesInterperiod_s = int(data['queriesInterperiod_s'])
        indexExps = int(data['indexExps'])

        idExpsConfig=db.CampaignGetExpsConfigIdByID(idCampaign)
        idPufsConfig=db.ExpsConfigGetPufsConfigIdByID(idExpsConfig)
        idDevice=db.CampaignGetDeviceIdByID(idCampaign)
        ipAddress=db.DeviceGetIPById(idDevice)
        filePufsConfigXML = genericPufsConfig + str(idPufsConfig) + '/configuration.xml'
        numByteChallenge = cf.XMLPufsConfigGetChalNumBytes(filePufsConfigXML,pufIds[0])

        while indexExps < numExps:
            indexChal = int(data['indexChal'])
            # Internal cycle on challenges
            while step*indexChal < 2**challengeBitsWidth:
                challenge = step*indexChal
                pcktToSend = BuildQueryCommPayload(idCampaign,pufIds,indexExps,numByteChallenge,challenge)
                ds.EnqueueCommandToSend(False,ipAddress,PUF_QURY_REQ,pcktToSend)

                logger.debug("Enqueued a query command with challenge %d to %s.",challenge,ipAddress)

                # Scrivi indexChal nel file di snapshot (come modulo del numero di chal però)
                data['indexChal'] = (indexChal + 1)%(2**challengeBitsWidth)
                indexChal+=1
                WriteJsonFile(snapshotFile,data)
                if stopExpThread.is_set():
                    logger.warning("Aborted a range-type experiment!")
                    return False
                logger.debug("Waiting %d seconds for the next query command.",queriesInterperiod_s)
                # wait queries_interperiod_s seconds between queries
                time.sleep(queriesInterperiod_s)

            # wait exp_interperiod_m minutes between experiments
            logger.info("The iteration nr. %d of the range-type experiment is terminated.",indexExps)
            logger.debug("Waiting %d minutes for the next experiment run",expInterperiod_m)
            indexExps+=1
            #Scrivi nel file di snapshot esatta mente questo numero senza modulo
            data['indexExps'] = indexExps
            WriteJsonFile(snapshotFile,data)
            if indexExps < numExps:
                time.sleep(expInterperiod_m * 60)
        
        
        logger.info(f"Range-type experiment with idCampaign {idCampaign} for pufIds {pufIds} is terminated!")
        # Remove the snapshot file after all iterations are complete
        os.remove(snapshotFile)
        logger.debug("Snapshot file %s has been deleted",snapshotFile)
        return True
    
    except Exception as e:
        logger.error("Error during range-type experiment: %s", str(e))
        return False

def RunChalRandomExp(snapshotFile):
    """!
    @brief The function implements the thread logic used by the server 
            to perform experiments of type 'random'.
    @details Starting with a snapshot file in which the information useful 
            for running the experiments is stored, the function initializes 
            its local variables and then starts the loop in which it factually 
            queues the query commands to be sent to the device. 
            It should be noted that at each iteration the snapshot file is updated and 
            it is checked to see if the experiment interrupting event has been set.

    Parameters : 
        @param snapshotFile => The file used as snapshot to save the progress of the experiment.
        @param stopExpThread => Interrupting event.

    """
    try:
        data = ReadJsonFile(snapshotFile)
        idCampaign = _GetPufCampIdsFromSnapshot(snapshotFile)
        pufIds = data['puf_ids']
        logger.info(f"Initialization of a new thread associated to a random-type experiment. IdCampaign={idCampaign}, pufIds={pufIds}.")

        challenges = data['challenges']
        numExps = data['numExps']
        expInterperiod_m = data['expInterperiod_m']
        queriesInterperiod_s = data['queriesInterperiod_s']
        indexExps = data['indexExps']
        indexChal = data['indexChal']

        idExpsConfig=db.CampaignGetExpsConfigIdByID(idCampaign)
        idPufsConfig=db.ExpsConfigGetPufsConfigIdByID(idExpsConfig)
        idDevice=db.CampaignGetDeviceIdByID(idCampaign)
        ipAddress=db.DeviceGetIPById(idDevice)
        filePufsConfigXML = genericPufsConfig + str(idPufsConfig) + '/configuration.xml'
        numByteChallenge = cf.XMLPufsConfigGetChalNumBytes(filePufsConfigXML,pufIds[0])

        while indexExps < numExps:
            indexChal = int(data['indexChal'])
            # Internal cycle on challenges
            while indexChal < len(challenges):
                challenge = challenges[indexChal]
                pcktToSend = BuildQueryCommPayload(idCampaign,pufIds,indexExps,numByteChallenge,challenge)
                ds.EnqueueCommandToSend(False,ipAddress,PUF_QURY_REQ,pcktToSend)

                logger.debug("Enqueued a query command with challenge %d to %s.",challenge,ipAddress)

                # Scrivi indexChal nel file di snapshot (come modulo del numero di chal però)
                data['indexChal'] = (indexChal + 1)%(len(challenges))
                indexChal+=1
                WriteJsonFile(snapshotFile,data)
                if stopExpThread.is_set():
                    logger.warning("Aborted a random experiment!")
                    return False
                logger.debug("Waiting %d seconds for the next query command.",queriesInterperiod_s)
                # wait queries_interperiod_s seconds between queries
                time.sleep(queriesInterperiod_s)

            # wait exp_interperiod_m minutes between experiments
            logger.info("The iteration nr. %d of the random-type experiment is terminated.",indexExps)
            logger.debug("Waiting %d minutes for the next experiment run",expInterperiod_m)
            indexExps+=1
            #Scrivi nel file di snapshot esatta mente questo numero senza modulo
            data['indexExps'] = indexExps
            WriteJsonFile(snapshotFile,data)
            if indexExps < numExps:
                time.sleep(expInterperiod_m * 60)

        logger.info(f"Random-type experiment with idCampaign {idCampaign} for pufIds {pufIds} is terminated!")
        # Remove the snapshot file after all iterations are complete
        os.remove(snapshotFile)
        logger.debug("Snapshot file %s has been deleted",snapshotFile)
        return True
    
    except Exception as e:
        logger.error("Error during random-type experiment: %s", str(e))
        return False

def RunChalListExp(snapshotFile):
    """!
    @brief [Function's description]

    Parameters : 
        @param snapshotFile => [description]
        @param stopExpThread => [description]

    """
    """!
    @brief The function implements the thread logic used by the server 
            to perform experiments of type 'list'.
    @details Starting with a snapshot file in which the information useful 
            for running the experiments is stored, the function initializes 
            its local variables and then starts the loop in which it factually 
            queues the query commands to be sent to the device. 
            It should be noted that at each iteration the snapshot file is updated and 
            it is checked to see if the experiment interrupting event has been set.

    Parameters : 
        @param snapshotFile => The file used as snapshot to save the progress of the experiment.
        @param stopExpThread => Interrupting event.

    """
    try:
        data = ReadJsonFile(snapshotFile)
        idCampaign = _GetPufCampIdsFromSnapshot(snapshotFile)
        pufIds = data['puf_ids']
        logger.info(f"Initialization of a new thread associated to a list-type experiment. IdCampaign={idCampaign}, pufIds={pufIds}.")

        challenges = data['challenges']
        numExps = data['numExps']
        expInterperiod_m = data['expInterperiod_m']
        queriesInterperiod_s = data['queriesInterperiod_s']
        indexExps = data['indexExps']

        idExpsConfig=db.CampaignGetExpsConfigIdByID(idCampaign)
        idPufsConfig=db.ExpsConfigGetPufsConfigIdByID(idExpsConfig)
        idDevice=db.CampaignGetDeviceIdByID(idCampaign)
        ipAddress=db.DeviceGetIPById(idDevice)
        filePufsConfigXML = genericPufsConfig + str(idPufsConfig) + '/configuration.xml'
        numByteChallenge = cf.XMLPufsConfigGetChalNumBytes(filePufsConfigXML,pufIds[0])

        while indexExps < numExps:
            indexChal = int(data['indexChal'])
            # Internal cycle on challenges
            while indexChal < len(challenges):
                challenge = challenges[indexChal]
                pcktToSend = BuildQueryCommPayload(idCampaign,pufIds,indexExps,numByteChallenge,challenge)
                ds.EnqueueCommandToSend(False,ipAddress,PUF_QURY_REQ,pcktToSend)

                logger.debug("Enqueued a query command with challenge %d to %s.",challenge,ipAddress)

                # Scrivi indexChal nel file di snapshot (come modulo del numero di chal però)
                data['indexChal'] = (indexChal + 1)%(len(challenges))
                indexChal+=1
                WriteJsonFile(snapshotFile,data)
                if stopExpThread.is_set():
                    logger.warning("Aborted a list experiment!")
                    return False
                logger.debug("Waiting %d seconds for the next query command.",queriesInterperiod_s)
                # wait queries_interperiod_s seconds between queries
                time.sleep(queriesInterperiod_s)

            # wait exp_interperiod_m minutes between experiments
            logger.info("The iteration nr. %d of the list-type experiment is terminated.",indexExps)
            logger.debug("Waiting %d minutes for the next experiment run",expInterperiod_m)
            indexExps+=1
            #Scrivi nel file di snapshot esatta mente questo numero senza modulo
            data['indexExps'] = indexExps
            WriteJsonFile(snapshotFile,data)
            if indexExps < numExps:
                time.sleep(expInterperiod_m * 60)
        
        logger.info(f"List-type experiment with idCampaign {idCampaign} for pufIds {pufIds} is terminated!")
        # Remove the snapshot file after all iterations are complete
        os.remove(snapshotFile)
        logger.debug("Snapshot file %s has been deleted",snapshotFile)
        return True
    
    except Exception as e:
        logger.error("Error during list-type experiment: %s", str(e))
        return False

def ResetThreadStopEvent():
    stopExpThread.clear()

def AbortExperiments():
    """!
    @brief The function sets the interrupting event 
            to abort all threads of ongoing experiments.


    """
    stopExpThread.set()
    logger.warning("Sent abort signal to all exp threads!")

def _GetPufCampIdsFromSnapshot(filename):
    """!
    @brief The function returns idCampaign from a snapshot file <filename>.

    Parameters : 
        @param filename => Snapshot file.

    """
    # Estrai il nome base del file dal percorso completo
    basename = os.path.basename(filename)
    # Usa una regex per trovare idCampaign
    match = re.match(r'run_(\d+)\.json', basename)

    if match:
        idCampaign = int(match.group(1))
        return idCampaign
    else:
        raise ValueError("The name of the file is not in the form 'run_<idCampaign>.json'")
