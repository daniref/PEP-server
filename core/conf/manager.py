from core.utility import utility
from core.utility import packets as pk
from core.conf.conf import *
from core import exps as ex
from core import datastruct as ds
from db import dbAPI as db
from threading import current_thread

from concurrent.futures import ThreadPoolExecutor, as_completed

# Ottieni un logger per il modulo corrente
logger = logging.getLogger(__name__)

def HandlePufsConfigCommand(idDevice, xmlPufsConfig, idpufsConfig):
    logger.debug("Enqueuing Pufs Config command to device(id): %s ",idDevice)
    devAddress = db.DeviceGetIPById(idDevice)
    data = pk.BuildPufsConfigPayload(xmlPufsConfig, idpufsConfig)

    ds.EnqueueCommandToSend(False,devAddress,PUF_CONF_REQ,data)
    logger.debug("Pufs Config Command enqueued!")

def HandleExpsConfigCommand(idCampaign, expsConfigXML):
    idDevice=db.CampaignGetDeviceIdByID(idCampaign)
    logger.debug("Enqueuing Exps Config command to device(id): %s ",idDevice)
    # delay = 11
    # num_dev = 6
    # logger.debug(f'I am waiting {delay} seconds before starting experiments for device {idDevice}')
    # time.sleep(delay*(num_dev-(idDevice-3)))

    xmlParsed = etree.parse(expsConfigXML)
    rootElem = xmlParsed.getroot()
    
    rangeExps = xmlParsed.findall(".//RangeExp")
    listExps = xmlParsed.findall(".//ListExp")
    randomExps = xmlParsed.findall(".//RandomExp")
    numExpInstances = len(rangeExps) + len(listExps) + len(randomExps)

    logger.info("Number of instances found(id): %d ",numExpInstances)

    # Utilizza ThreadPoolExecutor per gestire i thread
    with ThreadPoolExecutor(max_workers=numExpInstances) as executor:
        newExpThreadsList = []

        for pufIndex, exp in enumerate(rootElem):
            if exp.tag == 'ListExp':
                logger.debug("Starting creation of new exp list thread")
                puf_ids = []
                challenges =  []
                numExps = None
                expInterperiod_m = None
                queriesInterperiod_s = None
                # Find all puf ids elements and store their values in a list
                for id in exp.find('puf_ids').findall('id'):
                    puf_ids.append(int(id.text))

                # Find all challenge elements and store their values in a list
                for challenge in exp.find('challenges_list').findall('challenge'):
                    challenges.append(int(challenge.text))

                # Get other elements' values
                numExps = int(exp.find('num_exps').text)
                expInterperiod_m = int(exp.find('exp_interperiod_m').text)
                queriesInterperiod_s = int(exp.find('queries_interperiod_s').text)
                indexExps = 0
                indexChal = 0

                # Load template for challenges list exp
                listTemplate = runningExpsDirectory + '/list/template.json'
                logger.debug("List template snapshot to open: %s ",listTemplate)

                with open(listTemplate, 'r') as file:
                    template = json.load(file)
                logger.debug("Snapshot loaded: %s ",listTemplate)

                # Update values
                template['puf_ids'] = puf_ids
                template['challenges'] = challenges
                logger.debug("Snapshot: Challenges loaded: %s", ", ".join(map(str, challenges)))

                template['numExps'] = numExps
                logger.debug("Snapshotrexps: %d ",numExps)

                template['expInterperiod_m'] = expInterperiod_m
                logger.debug("Snapshot: expInterperiod_m: %d ",expInterperiod_m)

                template['queriesInterperiod_s'] = queriesInterperiod_s
                logger.debug("Snapshot: queriesInterperiod_s: %d ",queriesInterperiod_s)

                template['indexExps'] = indexExps
                logger.debug("Snapshot: indexExps: %d ",indexExps)

                template['indexChal'] = indexChal
                logger.debug("Snapshot: indexChal: %d ",indexChal)

                snapshotFile = runningExpsDirectory + '/list/run_' + str(idCampaign) + '.json'
                logger.debug("Creating snapshot file: %s ",snapshotFile)

                # Salva il template aggiornato in un nuovo file JSON
                with open(snapshotFile, 'w') as file:
                    json.dump(template, file, indent=4)

                logger.debug("Created new list challenge exp snapshot: %s ",snapshotFile)

                # Crea un thread per ogni istanza e lo aggiunge alla lista di futures
                newExpThreadsList.append(executor.submit(ex.RunChalListExp, snapshotFile))

            if exp.tag == 'RandomExp':
                logger.debug("Starting creation of new exp random thread")
                
                puf_ids = []
                # Find all puf ids elements and store their values in a list
                for id in exp.find('puf_ids').findall('id'):
                    puf_ids.append(int(id.text))

                challengesRange = int(exp.find('challenges_range').text)
                # Preleva il campo randomSeed
                randomSeedField = exp.find('random_seed')

                # Verifica se il campo random_seed è vuoto
                if randomSeedField is not None and not randomSeedField.text:
                    randomSeed = int(time.time())
                    logger.debug("Seed not specified, timestamp %d is used!", randomSeed)
                else:
                    randomSeed = int(randomSeedField.text)
                    logger.debug("Seed %d specified!", randomSeed)

                numExps = int(exp.find('num_exps').text)
                expInterperiod_m = int(exp.find('exp_interperiod_m').text)
                numChallenges = int(exp.find('num_challenges').text)
                queriesInterperiod_s = int(exp.find('queries_interperiod_s').text)
                indexExps = 0
                indexChal = 0
                
                rng = np.random.default_rng(randomSeed)  # Crea un generatore di numeri casuali con il seed specifico
                challenges = rng.integers(0, 2**challengesRange, numChallenges).tolist()

                # Load template for challenges random exp
                randomTemplate = runningExpsDirectory + '/random/template.json'
                logger.debug("Random template snapshot to open: %s ",randomTemplate)

                with open(randomTemplate, 'r') as file:
                    template = json.load(file)
                logger.debug("Snapshot loaded: %s ",randomTemplate)

                # Update values
                template['puf_ids'] = puf_ids
                template['challenges'] = challenges
                template['numExps'] = numExps
                template['expInterperiod_m'] = expInterperiod_m
                template['queriesInterperiod_s'] = queriesInterperiod_s
                template['indexExps'] = indexExps
                template['indexChal'] = indexChal
                
                snapshotFile = runningExpsDirectory + '/random/run_' + str(idCampaign) + '.json'
                # Salva il template aggiornato in un nuovo file JSON
                with open(snapshotFile, 'w') as file:
                    json.dump(template, file, indent=4)

                logger.debug("Created new random challenge exp snapshot: %s ",snapshotFile)

                # Crea un thread per ogni istanza e lo aggiunge alla lista di futures
                newExpThreadsList.append(executor.submit(ex.RunChalRandomExp, snapshotFile))

            if exp.tag == 'RangeExp':
                logger.debug("Starting creation of new exp range thread")
                
                puf_ids = []
                challengeBitsWidth = None
                step = None
                numExps = None
                expInterperiod_m = None
                queriesInterperiod_s = None
                indexExps = None
                indexChal = None

                # Get values
                # Find all puf ids elements and store their values in a list
                for id in exp.find('puf_ids').findall('id'):
                    puf_ids.append(int(id.text))
                challengeBitsWidth = int(exp.find('challenge_bits_width').text)
                step = int(exp.find('step').text)
                numExps = int(exp.find('num_exps').text)
                expInterperiod_m = int(exp.find('exp_interperiod_m').text)
                queriesInterperiod_s = int(exp.find('queries_interperiod_s').text)
                indexExps = 0
                indexChal = 0

                # Load template for challenges list exp
                rangeTemplate = runningExpsDirectory + '/range/template.json'
                logger.debug("Range template snapshot to open: %s ",rangeTemplate)

                with open(rangeTemplate, 'r') as file:
                    template = json.load(file)
                logger.debug("Snapshot loaded: %s ",rangeTemplate)

                # Update values
                template['puf_ids'] = puf_ids
                template['challengeBitsWidth'] = challengeBitsWidth
                logger.debug("Snapshot: Challenges bits width: %d", challengeBitsWidth)

                template['step'] = step
                logger.debug("Snapshot: Step: %d", step)

                template['numExps'] = numExps
                logger.debug("Snapshot: Num exps: %d ",numExps)

                template['expInterperiod_m'] = expInterperiod_m
                logger.debug("Snapshot: expInterperiod_m: %d ",expInterperiod_m)

                template['queriesInterperiod_s'] = queriesInterperiod_s
                logger.debug("Snapshot: queriesInterperiod_s: %d ",queriesInterperiod_s)

                template['indexExps'] = indexExps
                logger.debug("Snapshot: indexExps: %d ",indexExps)

                template['indexChal'] = indexChal
                logger.debug("Snapshot: indexChal: %d ",indexChal)

                snapshotFile = runningExpsDirectory + '/range/run_' + str(idCampaign) + '.json'
                logger.debug("Creating snapshot file: %s ",snapshotFile)

                # Salva il template aggiornato in un nuovo file JSON
                with open(snapshotFile, 'w') as file:
                    json.dump(template, file, indent=4)

                logger.debug("Created new range challenge exp snapshot: %s ",snapshotFile)

                # Crea un thread per ogni istanza e lo aggiunge alla lista di futures
                
                myexecutor = executor.submit(ex.RunChalRangeExp, snapshotFile)
                logger.info(f"Status thread excutor: {myexecutor}")
                newExpThreadsList.append(myexecutor)

        allThreadsSuccessfull = True
        # Aspetta che tutti i thread siano completati
        for future in as_completed(newExpThreadsList):

			# Puoi gestire eventuali eccezioni qui se necessario
            try:
                result = future.result()
                if not result:
                    allThreadsSuccessfull = False
            except Exception as e:
                logger.error("Error occurred in an exp thread: %s",e)
                allThreadsSuccessfull = False
    if(allThreadsSuccessfull):
        # Una volta che tutti i thread sono completati, chiama freeDevice
        time.sleep(COMPLETE_EXEC_COMMAND_TIME)
        ereasedCommands = ds.EreaseAllPendingCommandsOfIdCampaign(idCampaign)
        logger.warning("%d commands deleted of Campaign <%d>",ereasedCommands,idCampaign)
        db.CampaignSetEndDate(idCampaign)
        db.DeviceFreeDeviceById(idDevice)
        logger.info("Experimental campaign #%d correctly completed!",idCampaign)
    else:
        logger.warning("Experimental campaign #%d not yet completed!",idCampaign)