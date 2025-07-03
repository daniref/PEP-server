# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.db.models import Q
from django.db.models import F
from datetime import *
import pytz
from .dbmodels import *

localTz = pytz.timezone('Europe/Rome')

# CRP API
def CRPInsert(expcampaign, idpuf, numRep, challenge, response, counter1, counter2, temperature, voltage):
    # Creazione di una nuova istanza del modello Crp
    newEntry = Crp(
        expcampaign=expcampaign,  # Imposta l'id della campagna
        idpuf=idpuf,
        numrep=numRep,
        challenge=challenge,
        response=response,
        counter1=counter1,
        counter2=counter2,
        temperature=temperature,
        voltage=voltage,
        timestamp=datetime.now(localTz)  # Imposta il timestamp corrente
    )
    
    # Salvataggio della nuova entry nel database
    newEntry.save()

    # Ritorna l'id della nuova entry appena inserita
    return newEntry.idcrp

def CRPDeleteByIdCRP(idCRP):
    try:
        # Cerca l'entry usando la chiave primaria
        crp = Crp.objects.get(pk=idCRP)
        # Cancella l'entry
        crp.delete()
        # Restituisce True se l'entry è stata cancellata con successo
        return True
    except crp.DoesNotExist:
        # Se l'entry non esiste, restituisci False
        return False

def CRPGetCRPsByIdCampaign(idCampaign):
    return Crp.objects.filter(expcampaign_id=idCampaign).exclude(expcampaign=None).values(
        *[field.name for field in Crp._meta.fields if field.name != 'expcampaign']        
    )


# Campaign API
def CampaignInsert(conductedby, deviceused, expsconfiguration):
    # Creazione di una nuova istanza del modello Crp
    newEntry = Campaign(
        conductedby=conductedby,
        deviceused=deviceused,
        expsconfiguration=expsconfiguration,
        startdate=str(datetime.now(localTz).date())
    )
    
    # Salvataggio della nuova entry nel database
    newEntry.save()

    # Ritorna l'id della nuova entry appena inserita
    return newEntry.idcampaign

def CampaignDeleteByIdCampaign(idCampaign):
    try:
        # Cerca l'entry usando la chiave primaria
        campaign = Campaign.objects.get(pk=idCampaign)
        # Cancella l'entry
        campaign.delete()
        # Restituisce True se l'entry è stata cancellata con successo
        return True
    except campaign.DoesNotExist:
        # Se l'entry non esiste, restituisci False
        return False

def CampaignGetExpsConfigIdByID(idCampaign):
    return Campaign.objects.get(pk=idCampaign).expsconfiguration_id

def CampaignGetDeviceIdByID(idCampaign):
    return Campaign.objects.get(pk=idCampaign).deviceused_id

def CampaignGetCampaignByID(idCampaign):
    try:
        campaign = Campaign.objects.filter(pk=idCampaign).first()
        return campaign
    except Campaign.DoesNotExist:
        return None

def CampaignSetEndDate(idCampaign):
    campaign = Campaign.objects.get(pk=idCampaign)
    campaign.enddate = datetime.now(localTz).date()
    campaign.save()

#Device API         
def DeviceInsert(macaddress, ipaddress, vendor, model, fpga, state):
    
    # Creazione di una nuova istanza del modello Crp
    newEntry = Device(
        macaddress = macaddress,
        ipaddress = ipaddress,
        vendor=vendor,
        model=model,
        fpga=fpga,
        state=state
        )
    # Salvataggio della nuova entry nel database
    newEntry.save()
    # Ritorna l'id della nuova entry appena inserita
    return newEntry.iddevice

def DeviceDeleteByIdDevice(idDevice):
    try:
        # Cerca l'entry usando la chiave primaria
        device = Device.objects.get(pk=idDevice)
        # Cancella l'entry
        device.delete()
        # Restituisce True se l'entry è stata cancellata con successo
        return True
    except Device.DoesNotExist:
        # Se l'entry non esiste, restituisci False
        return False

def DeviceDeleteByMAC(macaddress):
    try:
        # Cerca l'entry usando la chiave primaria
        device = Device.objects.get(pk=macaddress)
        # Cancella l'entry
        device.delete()
        # Restituisce True se l'entry è stata cancellata con successo
        return True
    except Device.DoesNotExist:
        # Se l'entry non esiste, restituisci False
        return False
    
def DeviceIsRegByMAC(macaddress):
    device = Device.objects.filter(Q(macaddress=macaddress)).first()
    if device is not None:
        return True
    else:
        return False

def DeviceUpdateIPByMAC(macAddress,devAddress):
    device = Device.objects.filter(Q(macaddress=macAddress)).first()
    device.ipaddress=devAddress
    device.save()

def DeviceUpdateStateByMAC(macAddress,state):
    device = Device.objects.filter(Q(macaddress=macAddress)).first()
    device.state=state
    device.save()  

def DeviceIsUsedByMAC(macAddress):
    device = Device.objects.filter(Q(macaddress=macAddress)).first()
    if device.usedby is None:
        return False
    else:
        return True

def DeviceGetFreeList():
    # Utilizza il modello Device per ottenere gli elementi disponibili
    devicesAvailable = Device.objects.filter(state='available', usedby__isnull=True)
    # Restituisci una lista degli elementi disponibili
    return list(devicesAvailable)

def DeviceSetStateById(idDevice,state):
    device = Device.objects.filter(Q(iddevice=idDevice)).first()
    device.state=state
    device.save()

def DeviceSetUserById(idDevice, User):
    device = Device.objects.filter(Q(iddevice=idDevice)).first()
    device.usedby=User
    device.save()

def DeviceGetIPById(idDevice):
    return Device.objects.get(pk=idDevice).ipaddress

def DeviceGetIdByAddress(address):
    device = Device.objects.filter(Q(ipaddress=address)).first()
    return device.iddevice

def DeviceGetUserbyId(idDevice):
    return Device.objects.get(pk=idDevice).usedby

def DeviceSetAllStateUnreachable():
    Device.objects.all().update(state='unreachable')

def DeviceGetDeviceById(idDevice):
    try:
        device = Device.objects.filter(pk=idDevice).first()
        return device
    except Device.DoesNotExist:
        return None

def DeviceFreeDeviceById(idDevice):
    device = Device.objects.get(pk=idDevice)
    device.state='available'
    device.usedby=None
    device.save()

def DeviceIsReady(idDevice):
    device = Device.objects.get(pk=idDevice)
    if device.state == 'ready':
        return True
    else:
        return False

def DeviceGetStateById(idDevice):
    return Device.objects.get(pk=idDevice).state

def DeviceGetReachableIP():
    reachableIPs = Device.objects.filter(~Q(state='unreachable')).values_list('ipaddress', flat=True)
    return list(reachableIPs)

def DeviceKeepAliveDBConnection():
    return Device.objects.all().count()

# Exps Conf API
def ExpsConfigInsert(User,pufsConfig):
   # Creazione di una nuova istanza del modello Configuration
    newEntry = Expsconfiguration(
        pufsconfiguration = pufsConfig,
        createdby = User,
        date=str(datetime.now(localTz).date())
    )
    
    # Salvataggio della nuova entry nel database
    newEntry.save()

    # Ritorna l'id della nuova entry appena inserita
    return newEntry.idexpsconfiguration 

def ExpsConfigDeleteByIdEC(idExpsConfig):
    try:
        # Cerca l'entry usando la chiave primaria
        config = Expsconfiguration.objects.get(pk=idExpsConfig)
        # Cancella l'entry
        config.delete()
        # Restituisce True se l'entry è stata cancellata con successo
        return True
    except config.DoesNotExist:
        # Se l'entry non esiste, restituisci False
        return False

def ExpsConfigGetExpsConfigById(idExpsConfig):
    try:
        expConf = Expsconfiguration.objects.filter(pk=idExpsConfig).first()
        return expConf
    except Expsconfiguration.DoesNotExist:
        return None    

def ExpsConfigGetPufsConfigIdByID(idExpsConfig):
    return Expsconfiguration.objects.get(pk=idExpsConfig).pufsconfiguration_id

# Pufs Conf API
def PufsConfigInsert(User):
   # Creazione di una nuova istanza del modello Configuration
    newEntry = Pufsconfiguration(
        createdby = User,
        date=str(datetime.now(localTz).date())
    )
    
    # Salvataggio della nuova entry nel database
    newEntry.save()

    # Ritorna l'id della nuova entry appena inserita
    return newEntry.idpufsconfiguration 

def PufsConfigDeleteByIdPC(idPufsConfig):
    try:
        # Cerca l'entry usando la chiave primaria
        config = Pufsconfiguration.objects.get(pk=idPufsConfig)
        # Cancella l'entry
        config.delete()
        # Restituisce True se l'entry è stata cancellata con successo
        return True
    except config.DoesNotExist:
        # Se l'entry non esiste, restituisci False
        return False

def PufsConfigGetConfById(idPufsConfig):
    try:
        conf = Pufsconfiguration.objects.filter(pk=idPufsConfig).first()
        return conf
    except Pufsconfiguration.DoesNotExist:
        return None

#User API
def UserInsert(username, password, firstname, lastname, email, affiliation):
    
    # Creazione di una nuova istanza del modello Crp
    newEntry = User(
        username=username,
        password=password,
        firstname=firstname,
        lastname=lastname,
        email=email,
        affiliation=affiliation,  # Imposta il timestamp corrente
        recorddate=str(datetime.now(localTz).date())
    )
    
    # Salvataggio della nuova entry nel database
    newEntry.save()

    # Ritorna l'id della nuova entry appena inserita
    return newEntry.iduser

def UserDeleteByIdUser(idUser):
    try:
        # Cerca l'entry usando la chiave primaria
        user = User.objects.get(pk=idUser)
        # Cancella l'entry
        user.delete()
        # Restituisce True se l'entry è stata cancellata con successo
        return True
    except User.DoesNotExist:
        # Se l'entry non esiste, restituisci False
        return False
        
def UserGetUsernameByIdUser(idUser):
    try:
        user = User.objects.get(pk=idUser)
        return (True,user.username)
    except User.DoesNotExist:
        return (False,0)

def UserGetUserByIdUser(idUser):
    try:
        user = User.objects.filter(pk=idUser).first()
        return user
    except User.DoesNotExist:
        return None

def UserGetIdUserByUsername(username):
    try:
        user = User.objects.get(username=username)
        return (True,user.iduser)
    except User.DoesNotExist:
        return (False,0)

def UserGetUserByUsername(username):
    return User.objects.get(username=username)

def UserGetPasswordByUsername(username):
    return User.objects.get(username=username).password
        
