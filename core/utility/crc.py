import struct
import logging

logger = logging.getLogger(__name__)

# Define the CRC-16 polynomial used for the calculation
crc16poly = 0x1021

def CalculateCRC16(data,poly16):
    """
    Calculates the CRC-16 checksum for the given data using the specified polynomial.
    :param data: The data for which to calculate the CRC.
    :param poly16: The polynomial to use for CRC calculation.
    :return: The calculated CRC-16 checksum as an integer.
    """
    crc = 0x0000  
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ poly16
            else:
                crc <<= 1

    return crc & 0xFFFF


def CheckMsgIntegrity(message):
    """
    Checks the integrity of a message by verifying its CRC.
    :param message: The message to check, which should end with a 2-byte CRC.
    :return: True if the CRC matches, False otherwise.
    """
    rcvdCRCBytes = message[-2:]  # take the last 2 bytes of the message as CRC
    rcvdCRC, = struct.unpack('>H', rcvdCRCBytes)  # Convert the bytes to an integer (big-endian)
    logger.debug("CRC to check %d.",rcvdCRC)
    calculatedCRC = CalculateCRC16(message[:-2],crc16poly)  # compute the CRC for the message excluding the last 2 bytes
    logger.debug("CRC calculated %d.", calculatedCRC)
    return rcvdCRC == calculatedCRC