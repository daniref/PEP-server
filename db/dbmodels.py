# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Crp(models.Model):
    idcrp = models.AutoField(db_column='idCRP', primary_key=True)  # Field name made lowercase.
    expcampaign = models.ForeignKey('Campaign', models.DO_NOTHING, db_column='expCampaign')  # Field name made lowercase.
    idpuf = models.IntegerField(db_column='idPuf')  # Field name made lowercase.
    numrep = models.IntegerField(db_column='numRep')  # Field name made lowercase.
    challenge = models.CharField(max_length=256)
    response = models.CharField(max_length=256)
    temperature = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    voltage = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    counter1 = models.CharField(max_length=256, blank=True, null=True)
    counter2 = models.CharField(max_length=256, blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        app_label = 'httpRequests'
        db_table = 'CRP'


class Campaign(models.Model):
    idcampaign = models.AutoField(db_column='idCampaign', primary_key=True)  # Field name made lowercase.
    conductedby = models.ForeignKey('User', models.DO_NOTHING, db_column='conductedBy')  # Field name made lowercase.
    deviceused = models.ForeignKey('Device', models.DO_NOTHING, db_column='deviceUsed')  # Field name made lowercase.
    expsconfiguration = models.ForeignKey('Expsconfiguration', models.DO_NOTHING, db_column='expsConfiguration')  # Field name made lowercase.
    startdate = models.DateField(db_column='startDate')  # Field name made lowercase.
    enddate = models.DateField(db_column='endDate', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        app_label = 'httpRequests'
        db_table = 'Campaign'


class Device(models.Model):
    iddevice = models.AutoField(db_column='idDevice', primary_key=True)  # Field name made lowercase. The composite primary key (idDevice, macAddress) found, that is not supported. The first column is selected.
    macaddress = models.CharField(db_column='macAddress', unique=True, max_length=17)  # Field name made lowercase.
    ipaddress = models.CharField(db_column='ipAddress', max_length=15)  # Field name made lowercase.
    vendor = models.CharField(max_length=45)
    model = models.CharField(max_length=45)
    fpga = models.TextField()
    state = models.CharField(max_length=11)
    usedby = models.ForeignKey('User', models.DO_NOTHING, db_column='usedBy', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        app_label = 'httpRequests'
        db_table = 'Device'
        unique_together = (('iddevice', 'macaddress'),)


class Expsconfiguration(models.Model):
    idexpsconfiguration = models.AutoField(db_column='idExpsConfiguration', primary_key=True)  # Field name made lowercase.
    pufsconfiguration = models.ForeignKey('Pufsconfiguration', models.DO_NOTHING, db_column='pufsConfiguration')  # Field name made lowercase.
    createdby = models.ForeignKey('User', models.DO_NOTHING, db_column='createdBy')  # Field name made lowercase.
    date = models.DateField()

    class Meta:
        managed = False
        app_label = 'httpRequests'
        db_table = 'ExpsConfiguration'


class Pufsconfiguration(models.Model):
    idpufsconfiguration = models.AutoField(db_column='idPufsConfiguration', primary_key=True)  # Field name made lowercase.
    createdby = models.ForeignKey('User', models.DO_NOTHING, db_column='createdBy')  # Field name made lowercase.
    date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        app_label = 'httpRequests'
        db_table = 'PufsConfiguration'


class User(models.Model):
    iduser = models.AutoField(db_column='idUser', primary_key=True)  # Field name made lowercase.
    username = models.CharField(unique=True, max_length=45)
    password = models.CharField(unique=True, max_length=256)
    firstname = models.CharField(db_column='firstName', max_length=45)  # Field name made lowercase.
    lastname = models.CharField(db_column='lastName', max_length=45)  # Field name made lowercase.
    email = models.CharField(max_length=45)
    affiliation = models.CharField(max_length=45, blank=True, null=True)
    recorddate = models.DateField(db_column='recordDate')  # Field name made lowercase.

    class Meta:
        managed = False
        app_label = 'httpRequests'
        db_table = 'User'
