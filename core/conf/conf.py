from lxml import etree
import math

from core.utility.utility import *
from db import dbAPI as db


logger = logging.getLogger(__name__)        # Initialize the logger for the module

pufsConfigSchema = pufsConfigDirectory + "/PufsConfigSchema.xsd"
expsConfigSchema = expsConfigDirectory + "/ExpsConfigSchema.xsd"

PUFS_CONF = 'pufsConf'
EXPS_CONF = 'expsConf'

def ValidateXMLConfigs(xmlFile,xmlType):
    """!
    @brief The function validates an xml configuration 
            received from a client, using the appropriate 
            xsd schema based on the type of configuration to be validated.

    Parameters : 
        @param xmlFile => Xml file to be validated.
        @param xmlType => Type of configuration to be validated.

    @return True The xml configuration is valid.
    @return False The xml configuration is not valid.

    """
    try:
        if(xmlType == 'pufsConf'):
            validator=pufsConfigSchema
        elif(xmlType=='expsConf'):
            validator=expsConfigSchema
        else:
            logger.error("XML type not valid.")
            return False

        # Carica il documento XML
        xmlschema_doc = etree.parse(validator)

        # Carica lo schema XSD
        xmlschema = etree.XMLSchema(xmlschema_doc)

        # Parsa il documento XML da validare
        xml_doc = etree.parse(xmlFile)

        # Verifica se il documento XML è valido rispetto allo schema XSD
        is_valid = xmlschema.validate(xml_doc)

        if is_valid:
            logger.info("The xml configuration file is valid w.r.t. the xsd schema!")
            return True
        else:
            logger.warning("The xml configuration file is NOT valid w.r.t. the xsd schema!")
            return False

    except etree.XMLSchemaParseError as e:
        logger.error("Error while parsing the xsd schema: ", e)
        return False

    except etree.XMLSyntaxError as e:
        logger.error("Error while parsing the xml configuration file:", e)
        return False

def XMLPufsConfigGetChalNumBytes(xmlFile,numPuf):
    """!
    @brief The function returns the number of bytes of 
            the challenge of the puf having id <numpuf>, 
            found in the configuration xml file <xmlFile>.

    Parameters : 
        @param xmlFile => The xml file of pufs configuration.
        @param numPuf => The identifier of the puf, whose challenge 
                        you want to know the number of bytes.

    """
    xmlParsed = etree.parse(xmlFile)
    pufInstances = xmlParsed.findall(".//PUFInstance")
    bitsChalSize = int(pufInstances[numPuf].findtext('chalSize'))
    bytesChalSize = math.ceil(bitsChalSize / 8)
    return bytesChalSize

def XMLPufsConfigAreThereCountReg(idCampaign,idPuf):
    """!
    @brief The function returns a boolean value indicating 
        whether there are counter registers in the configuration of a puf 
        (example in the case of a ro puf).

    Parameters : 
        @param idCampaign => The identifier of the experimental campaign.
        @param idPuf => The identifier of the puf whose count registers 
                        you want to know about.

    """
    idExpsConfig=db.CampaignGetExpsConfigIdByID(idCampaign)
    idPufsConfig=db.ExpsConfigGetPufsConfigIdByID(idExpsConfig)
    filePufsConfigXML = genericPufsConfig + str(idPufsConfig) + '/configuration.xml'

    xmlParsed = etree.parse(filePufsConfigXML)
    pufInstances = xmlParsed.findall(".//PUFInstance")
    countSize = int(pufInstances[idPuf].findtext('countSize'))
    return countSize

def XMLExpsConfigGetNumExps(xmlFile):
   # Carica e fa il parsing del file XML
    tree = etree.parse(xmlFile)
    root = tree.getroot()

    # Ottieni tutti i nodi figli del tag <Exps>
    experiments = list(root)
    numExpsList = []
    
    for exp in experiments:
        numExps = exp.find('num_exps')
        if numExps is not None:
            try:
                numExpsList.append(int(numExps.text))  # Assicurati che sia un intero valido
            except ValueError:
                print(f"Valore non valido in <num_exps>: {numExps.text}")
        else:
            print("Campo <num_exps> non trovato nell'esperimento.")
    
    return numExpsList

def GetXMLExpConfigFile(idExpsConfig):
    """
    Cerca il file 'experiments.xml' nella sottodirectory 'expConfig_<idExpsConfig>'.

    Args:
        idExpsConfig (int): L'ID di configurazione da cercare.

    Returns:
        str: Il percorso completo del file 'experiments.xml' se esiste, altrimenti None.
    """
    # Costruisci il nome della sottocartella
    subdirName = f"expsConf_{idExpsConfig}"
    
    # Costruisci il percorso completo della sottocartella
    subirPath = os.path.join(expsConfigDirectory, subdirName)
    
    # Costruisci il percorso completo del file 'experiments.xml'
    newExpsConfFile = os.path.join(subirPath, 'experiments.xml')

    # Controlla se il file 'experiments.xml' esiste nella sottocartella
    if os.path.isfile(newExpsConfFile):
        print(f"File trovato: {newExpsConfFile}")
        return newExpsConfFile
    else:
        print(f"File 'experiments.xml' non trovato nella directory: {subirPath}")
        return None