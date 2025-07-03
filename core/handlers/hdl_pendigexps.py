from db import dbAPI as db
from core.power import power as pw
from core.utility.utility import *
from core import exps as ex
from core.conf import manager as mg
from core import datastruct as ds

from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures

logger = logging.getLogger(__name__)

def RetrievePendingExps():
    """
    This function retrieves the list of pending experimental campaigns and relaunches them.
    It checks the 'runningExpsDirectory' for subfolders 'list', 'random', and 'range',
    extracting the campaign IDs from the filenames that match the pattern 'run_<first_number>_<second_number>.json'.
    For each campaign ID found, it relaunches the experiments associated with that campaign.
    """
    idCampaignList = _ExtractIdOfPendingExpCamp()
    for idCamp in idCampaignList:
        exec.submit(_RelaunchExp, idCamp)

def _ExtractIdOfPendingExpCamp():
    """
    This function extracts the unique campaign IDs from the running experiments directory.
    It looks for subfolders 'list', 'random', and 'range', and matches filenames against the pattern
    'run_<first_number>_<second_number>.json'. It returns a list of unique campaign IDs.
    """
    subfolders = ['list', 'random', 'range']
    uniqueIdCampaign = set()

    # Regular expression to match the pattern run_<primo_numero>_<secondo_numero>.json
    pattern = re.compile(r'run_(\d+)_\d+\.json')

    for subfolder in subfolders:
        subfolderPath = os.path.join(runningExpsDirectory, subfolder)

        if not os.path.exists(subfolderPath):
            print(f"Subfolder {subfolderPath} does not exist.")
            continue

        for filename in os.listdir(subfolderPath):
            match = pattern.match(filename)
            if match:
                first_number = int(match.group(1))
                uniqueIdCampaign.add(first_number)

    return list(uniqueIdCampaign)

def _RelaunchExp(idCamp):
    """
    This function relaunches the experiments for a given campaign ID.
    It first checks if the campaign is active and retrieves the associated device and PUF configuration.
    It then waits for the device to be ready and relaunches the experiments using a ThreadPoolExecutor.
    If all experiments are successfully relaunched, it frees the device and marks the campaign as completed.
    """
    idExp = db.CampaignGetExpsConfigIdByID(idCamp)
    idPufConf = db.ExpsConfigGetPufsConfigIdByID(idExp)
    idDevice = db.CampaignGetDeviceIdByID(idCamp)
    pufsConfiguration =  genericPufsConfig + str(idPufConf) + '/configuration.xml'
    while(db.DeviceGetStateById(idDevice)!='unavailable'):
        time.sleep(30)
    # i'm sure the device is registered, so reachable
    mg.HandlePufsConfigCommand(idDevice,pufsConfiguration,idPufConf)
    while(db.DeviceGetStateById(idDevice)!='ready'):
        time.sleep(30)
    # i'm sure the device is registered, so ready to receive query request

    # Use ThreadPoolExecutor to run experiments concurrently
    with ThreadPoolExecutor() as exec:
        oldExpThreadsList = []
        logger.info("Now, I'm ready to relaunch experiments!")
        pendingIdPufExpList = _GetIdPufsOfPendingExps('list',idCamp)
        if(pendingIdPufExpList):
            for idPuf in pendingIdPufExpList:
                logger.info("Launching a List Exp with idCampaign %d for idPuf %d!",idCamp,idPuf)
                snapshotFile = os.path.join(runningExpsDirectory, 'list', f'run_{idCamp}_{idPuf}.json')
                oldExpThreadsList.append(exec.submit(ex.RunChalListExp, snapshotFile))
        else:
            logger.debug("No Exp List to relaunch!")

        pendingIdPufExpRandom = _GetIdPufsOfPendingExps('random',idCamp)
        if(pendingIdPufExpRandom):
            for idPuf in pendingIdPufExpRandom:
                logger.info("Launching a Random Exp with idCampaign %d for idPuf %d!",idCamp,idPuf)
                snapshotFile = os.path.join(runningExpsDirectory, 'random', f'run_{idCamp}_{idPuf}.json')
                oldExpThreadsList.append(exec.submit(ex.RunChalRandomExp, snapshotFile))
        else:
            logger.debug("No Random List to relaunch!")

        pendingIdPufExpRange = _GetIdPufsOfPendingExps('range',idCamp)
        if(pendingIdPufExpRange):
            for idPuf in pendingIdPufExpRange:
                logger.info("Launching a Range Exp with idCampaign %d for idPuf %d!",idCamp,idPuf)
                snapshotFile = os.path.join(runningExpsDirectory, 'range', f'run_{idCamp}_{idPuf}.json')
                oldExpThreadsList.append(exec.submit(ex.RunChalRangeExp, snapshotFile))
        else:
            logger.debug("No Range List to relaunch!")

        allThreadsSuccessfull = True
        # wait for all threads to complete
        for future in as_completed(oldExpThreadsList):

            try:
                result = future.result()
                if not result:
                    allThreadsSuccessfull = False
            except Exception as e:
                logger.error("Error occurred in an exp thread: %s",e)
                allThreadsSuccessfull = False
        
    if(allThreadsSuccessfull):
        # Once all experiments are relaunched, we can free the device and mark the campaign as completed
        time.sleep(COMPLETE_EXEC_COMMAND_TIME)
        ereasedCommands=ds.EreaseAllPendingCommandsOfIdCampaign(idCamp)
        logger.warning("%d commands deleted of Campaign <%d>",ereasedCommands,idCamp)
        db.CampaignSetEndDate(idCamp)
        db.DeviceFreeDeviceById(idDevice)
        logger.info("Experimental campaign #%d correctly completed!",idCamp)
    else:
        logger.warning("Experimental campaign #%d not yet completed!",idCamp)       
        

def _GetIdPufsOfPendingExps(expType,idCampaign):
    """
    This function retrieves the IDs of PUFs associated with pending experiments of a specific type
    (list, random, or range) for a given campaign ID. It searches in the corresponding subdirectory
    within the 'runningExpsDirectory' and matches filenames against the pattern 'run_<first_number>_<second_number>.json'.
    It returns a list of unique PUF IDs found in the filenames.
    """
    directoryToSearch = os.path.join(runningExpsDirectory,str(expType))
    logger.debug("Searching pendig %s exp in path %s ...",expType,directoryToSearch)

    # Regular expression to match the pattern run_<idCampaign>_<idPuf>.json
    filePattern = re.compile(r'run_{}_(\d+)\.json'.format(idCampaign))
    logger.debug("File pattern to search %s ",filePattern)

    idPufs = set()

    # cycle through the files in the directory
    for filename in os.listdir(directoryToSearch):
        match = filePattern.match(filename)
        if match:
            # add the PUF ID to the set
            idPufs.add(int(match.group(1)))

    # Convert the set to a list and return it
    return list(idPufs)

# Inizialize a ThreadPoolExecutor for running experiments concurrently
exec = concurrent.futures.ThreadPoolExecutor()

# do not forget to shutdown the executor when the program exits
import atexit
atexit.register(exec.shutdown)