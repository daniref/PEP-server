from django.shortcuts import render

# Create your views here.
import os
from django.contrib.auth.hashers import make_password
from django.http import HttpResponseNotFound, FileResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User  # O il tuo modello utente personalizzato
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

import logging
import io
import csv
import concurrent.futures

from db import dbAPI as db
from core.handlers.hdl_commands import *
from core.handlers.hdl_pendigexps import *
from core.utility.utility import *
from core.power.power import *
from core.conf import conf as cf
from core.conf import manager as mg

logger = logging.getLogger(__name__)

@require_http_methods(["GET"])
def BitstreamDownloading(request):
    # Ottieni la stringa di caratteri dal parametro nella richiesta GET
    idPufsConfig = request.GET.get('idpufsconfig')

    # Assicurati che il nome del file sia stato fornito
    if not idPufsConfig:
        return HttpResponseNotFound("'idpufsconfig' parameter not found")

    # Costruisci il percorso completo del file
    filePath = genericPufsConfig+idPufsConfig+"/bitstream.bin"
    logger.debug("Bitstream path requested %s",filePath)

    #Verifica se il file esiste
    if not os.path.exists(filePath):
        return HttpResponseNotFound("File not found")

    # Apre e restituisce il file come risposta HTTP
    try:
        with open(filePath, 'rb') as file:
            response = FileResponse(file)
            return HttpResponse(response)
    except Exception as e:
        return HttpResponseNotFound(f"Errore durante il recupero del file: {str(e)}")

 
@csrf_exempt
@require_http_methods(["POST"])
def ConfigFilesHandling(request):
############################CHECK PASSWORD###############################################    
    if request.method == 'POST':
        username = request.POST.get('username')
        rawPsw = request.POST.get('password')
        try:
            # Recupera l'utente dal database tramite lo username
            user = db.UserGetUserByUsername(username)
        except User.DoesNotExist:
            # Se l'utente non esiste, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid username'}, status=400)
        
        # Verifica la password inserita
        if check_password(rawPsw, db.UserGetPasswordByUsername(username)):
############################CHECK PASSWORD############################################### 
            logger.debug('Received new file %s', request.POST.get('type'))
            idUsr = request.POST.get('idUsr')
            logger.debug('Received file from idUsr %s',idUsr)   

            fileType = request.POST.get('type')
            logger.debug('Received file type %s',fileType)

            file = request.FILES['file']

            if idUsr and fileType and file:

                if fileType == cf.PUFS_CONF:
                    if(cf.ValidateXMLConfigs(file,cf.PUFS_CONF)):
                        user = db.UserGetUserByIdUser(idUsr)
                        idPufsConfig = db.PufsConfigInsert(user) # the id is related to the pufs configuration
                        newPufsConfDir =  genericPufsConfig + str(idPufsConfig)

                        os.makedirs(newPufsConfDir, exist_ok=True)
                        newPufsConfFile = newPufsConfDir + '/configuration.xml'
                    
                        with open(newPufsConfFile, 'wb') as destination: #saving file in the appropriate folder
                            for chunk in file.chunks():
                                destination.write(chunk)

                        logger.info('Saved new pufs config with id %d',idPufsConfig)
                        return JsonResponse({'result': True, 'idpufsconfig':idPufsConfig})
                    else:
                        logger.debug('XML Pufs Configuration not valid!')
                        return JsonResponse({'result': False})

                if fileType == 'bitstream':
                    idPufsConfig=request.POST.get('idpufsconfig')
                    pufsConfDir = genericPufsConfig + str(idPufsConfig)
                    if(os.path.exists(pufsConfDir)):
                        
                        newPufsBinFile = pufsConfDir + '/bitstream.bin'
                        logger.debug('Saving bitstream in %s!',newPufsBinFile)
                        with open(newPufsBinFile, 'wb') as destination: #saving file in the appropriate folder
                            for chunk in file.chunks():
                                destination.write(chunk)
                        logger.info('Bitstream saved correctly!')

                        return JsonResponse({'result': True})
                    else:
                        logger.debug('Configuration folder does not exist!')
                        return JsonResponse({'result': False})

                if fileType == EXPS_CONF:
                    idDev = request.POST.get('idDev')
                    if(ValidateXMLConfigs(file,EXPS_CONF)):
                        start_time = time.time()
                        idPufsConfig = request.POST.get('idpufsconfig')
                        pufsConfDir =  genericPufsConfig + str(idPufsConfig) + '/configuration.xml'
                        mg.HandlePufsConfigCommand(idDev,pufsConfDir,int(idPufsConfig))

                        pufsConf = db.PufsConfigGetConfById(idPufsConfig)
                        user = db.UserGetUserByIdUser(idUsr)
                        idExpsConfig = db.ExpsConfigInsert(user,pufsConf)
                        
                        newExpsConfDir =  '/' + genericExpsConfig + str(idExpsConfig)

                        os.makedirs(newExpsConfDir, exist_ok=True)
                        newExpsConfFile = newExpsConfDir + '/experiments.xml'
                    
                        with open(newExpsConfFile, 'wb') as destination: #saving file in the appropriate folder
                            for chunk in file.chunks():
                                destination.write(chunk)

                        logger.debug('Saved new exp conf with id %d',idExpsConfig)
                            # Lancia il lavoro in background
                        attempt=0
                        while attempt < thresholdDeviceReady:
                            if db.DeviceIsReady(idDev):
                                idCampaign = CreateNewExpCampaign(idDev,idExpsConfig)
                                
                                executor.submit(mg.HandleExpsConfigCommand, idCampaign,newExpsConfFile)
                                end_time = time.time()
                                period = end_time - start_time
                                print(f'Time to program a device {period}')
                                return JsonResponse({'result': True, 'idcampaign':idCampaign})
                            
                            attempt+=1
                            time.sleep(sToWaitDeviceReady)
                        db.DeviceFreeDeviceById(idDev)
                        logger.error('The device %s was not ready to run experiments',idDev)
                        return JsonResponse({'result': False})
                    
                    else:
                        logger.debug('Experiments Configuration not valid!')
                        db.DeviceFreeDeviceById(idDev)
                        return JsonResponse({'result': False})

            else:
                logger.error('Not all http post fields are present!')
                return JsonResponse({'result': False})

############################CHECK PASSWORD###############################################    
        else:
            # Se la password è errata, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid password'}, status=400)
    else:
        return JsonResponse({'result': False})
############################CHECK PASSWORD###############################################  


@csrf_exempt
@require_http_methods(["POST"])
def DevicesAvailability(request):  
############################CHECK PASSWORD###############################################    
    if request.method == 'POST':
        username = request.POST.get('username')
        rawPsw = request.POST.get('password')
        try:
            # Recupera l'utente dal database tramite lo username
            user = db.UserGetUserByUsername(username)
        except User.DoesNotExist:
            # Se l'utente non esiste, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid username'}, status=400)
        
        # Verifica la password inserita
        if check_password(rawPsw, db.UserGetPasswordByUsername(username)):
############################CHECK PASSWORD############################################### 

            if request.POST.get('idDevice'):
                # modify device availability
                User=db.UserGetUserByIdUser(request.POST.get('idUser'))
                db.DeviceSetStateById(request.POST.get('idDevice'),request.POST.get('state'))
                db.DeviceSetUserById(request.POST.get('idDevice'),User)
                return JsonResponse({'result': True})
            else:
                # Ottieni tutti i dispositivi disponibili dalla tabella Device
                devices = db.DeviceGetFreeList()
                # Converti i dispositivi in un elenco di dizionari
                serializedDev = [{'id': dev.iddevice, 'ip': dev.ipaddress, 'model': dev.model,'fpga':dev.fpga} for dev in devices]
                # Restituisci i dispositivi come una risposta JSON
                return JsonResponse(serializedDev, safe=False)

############################CHECK PASSWORD###############################################    
        else:
            # Se la password è errata, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid password'}, status=400)
    else:
        return JsonResponse({'result': False})
############################CHECK PASSWORD###############################################  

@csrf_exempt
@require_http_methods(["POST"])
def ExpCampaignDownloading(request):
############################CHECK PASSWORD###############################################    
    if request.method == 'POST':
        username = request.POST.get('username')
        rawPsw = request.POST.get('password')
        try:
            # Recupera l'utente dal database tramite lo username
            user = db.UserGetUserByUsername(username)
        except User.DoesNotExist:
            # Se l'utente non esiste, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid username'}, status=400)
        
        # Verifica la password inserita
        if check_password(rawPsw, db.UserGetPasswordByUsername(username)):
############################CHECK PASSWORD############################################### 
            idCampaign = request.POST.get('idCampaign')
            if(idCampaign):
                    # Recupera tutte le entry con l'idCampaign specificato
                    crpEntries = db.CRPGetCRPsByIdCampaign(idCampaign)
                    
                    # Se non ci sono entry, avvisa e ritorna una risposta vuota
                    if not crpEntries.exists():
                        return JsonResponse({'result': False, "error": "Nessuna entry trovata per idCampaign {}".format(idCampaign)}, status=404)
                    
                    # Creare un buffer in memoria per il CSV
                    buffer = io.StringIO()
                    
                    # Creare il writer CSV
                    writer = csv.writer(buffer, delimiter=fieldCSVDelimiter, lineterminator=lineCSVterminator)
                    
                    # Scrivi l'intestazione del CSV
                    headers = [field.name for field in db.Crp._meta.fields if field.name != 'expcampaign']
                    writer.writerow(headers)
                    
                    # Scrivi le righe del CSV
                    for entry in crpEntries:
                        row = [entry[field] for field in headers]
                        writer.writerow(row)
                    
                    # Tornare il buffer al punto di inizio
                    buffer.seek(0)
                    
                    # Convertire il contenuto del buffer in una stringa
                    csvBuffer = buffer.getvalue()
                    
                    # Restituire il contenuto CSV come parte della risposta JSON
                    return JsonResponse({'result':True, 'csv': csvBuffer,'field':fieldCSVDelimiter,'line':lineCSVterminator})

            else:
                logger.error('[CSV Request] - Id Campaign not specified!')
                return JsonResponse({'result': False})  
        
############################CHECK PASSWORD###############################################    
        else:
            # Se la password è errata, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid password'}, status=400)
    else:
        return JsonResponse({'result': False})
############################CHECK PASSWORD###############################################  
@csrf_exempt
@require_http_methods(["POST"])
def PowerHandling(request):
############################CHECK PASSWORD###############################################    
    if request.method == 'POST':
        username = request.POST.get('username')
        rawPsw = request.POST.get('password')
        try:
            # Recupera l'utente dal database tramite lo username
            user = db.UserGetUserByUsername(username)
        except User.DoesNotExist:
            # Se l'utente non esiste, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid username'}, status=400)
        
        # Verifica la password inserita
        if check_password(rawPsw, db.UserGetPasswordByUsername(username)):
############################CHECK PASSWORD############################################### 

            # Ottieni la stringa di caratteri dal parametro nella richiesta GET
            state = request.POST.get('state')
            item = request.POST.get('item')

            # Assicurati che il nome del file sia stato fornito
            if not state or not item:
                return HttpResponseNotFound("'item' and 'state' parameters not found")

            if item == 'device':
                if state == POWER_UP:
                    RetrievePendingExps()
                    result = PowerUpBoards()
                elif state == POWER_DOWN:
                    result = PowerDownBoards()
                else:
                    result = False
                    logger.error("[HTTP REQ] - PowerHandling() - State not recognized!")
            
            elif item == 'fan':
                if state == POWER_UP:
                    result = PowerUpFans()
                elif state == POWER_DOWN:
                    result = PowerDownFans()
                else:
                    result = False
                    logger.error("[HTTP REQ] - PowerHandling() - State not recognized!")
            else:
                result = False
                logger.error("[HTTP REQ] - PowerHandling() - Item not recognized!")
                
            return JsonResponse({'result': result})

############################CHECK PASSWORD###############################################    
        else:
            # Se la password è errata, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid password'}, status=400)
    else:
        return JsonResponse({'result': False})
############################CHECK PASSWORD###############################################  

@csrf_exempt
@require_http_methods(["POST"])
def GetNumExpsForIdCampaign(request):
############################CHECK PASSWORD###############################################    
    if request.method == 'POST':
        username = request.POST.get('username')
        rawPsw = request.POST.get('password')
        try:
            # Recupera l'utente dal database tramite lo username
            user = db.UserGetUserByUsername(username)
        except User.DoesNotExist:
            # Se l'utente non esiste, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid username'}, status=400)
        
        # Verifica la password inserita
        if check_password(rawPsw, db.UserGetPasswordByUsername(username)):
############################CHECK PASSWORD############################################### 
            # Ottieni l'id della campagna dalla richiesta GET
            idCampaign = request.POST.get('idcampaign')

            # Controlla se l'idCampaign è stato fornito
            if not idCampaign:
                return HttpResponseNotFound("'idcampaign' parameter not found")
            
            try:
                # Ottieni l'expConfigId dal database
                expConfigId = db.CampaignGetExpsConfigIdByID(idCampaign)
                
                # Ottieni il file XML della configurazione delle esperienze
                fileExpConfig = GetXMLExpConfigFile(expConfigId)
                
                # Se il file è stato trovato, calcola la lista di numExps
                if fileExpConfig is not None:
                    numExpsList = XMLExpsConfigGetNumExps(fileExpConfig)
                    return JsonResponse({'num_exps': numExpsList})
                else:
                    return HttpResponseNotFound("Experiment config file not found for idCampaign: " + idCampaign)
            
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)

############################CHECK PASSWORD###############################################    
        else:
            # Se la password è errata, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid password'}, status=400)
    else:
        return JsonResponse({'result': False})
############################CHECK PASSWORD###############################################  

@csrf_exempt
@require_http_methods(["POST"])
def UserRegistration(request):  
    if (request.method == 'POST'):
        if request.POST:
            # enter new user entry
            searchResult = db.UserGetIdUserByUsername(request.POST.get('username'))
            if(True == searchResult[0]):
                logger.info('User with username %s is already registered with id %d!', request.POST.get('username'), searchResult[1])
                return JsonResponse({'result': False, 'idUser': searchResult[1]})
            else:
                idUser = db.UserInsert(request.POST.get('username'),make_password(request.POST.get('password')), request.POST.get('firstname'), request.POST.get('lastname'), request.POST.get('email'), request.POST.get('affiliation'))
                logger.info('New user has been registered with id %d', idUser)
                return JsonResponse({'result': True, 'idUser': idUser})

    else:
        # Se la richiesta non è una richiesta GET, restituisci un errore
        return JsonResponse({'error': 'Method not supported'}, status=405)

@csrf_exempt
@require_http_methods(["POST"])
def LogInUser(request):
    username = request.POST.get('username')
    rawPsw = request.POST.get('password')
    if request.method == 'POST':      
        # Verifica la password inserita
        if check_password(rawPsw, db.UserGetPasswordByUsername(username)):
            return JsonResponse({'result': True, 'idUser': db.UserGetIdUserByUsername(username)[1]})
        else:
            # Se la password è errata, restituisci un errore
            return JsonResponse({'result': False, 'error': 'Invalid password'}, status=400)
    else:
        return JsonResponse({'result': False})
    
def CreateNewExpCampaign(idDevice,idExpsConfig):
    user = db.DeviceGetUserbyId(idDevice)
    expConfig = db.ExpsConfigGetExpsConfigById(idExpsConfig)
    device = db.DeviceGetDeviceById(idDevice)
    idCampaign = db.CampaignInsert(user,device,expConfig)
    return idCampaign

# Inizializza un ThreadPoolExecutor globale
executor = concurrent.futures.ThreadPoolExecutor(max_workers=500) #TODO: change if you want more executors

# Non dimenticare di spegnere l'executor quando il server si spegne
import atexit
atexit.register(executor.shutdown)