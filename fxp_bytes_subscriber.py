"""
Aditya Ganti

This module contains useful un-marshalling functions for manipulating Forex Provider packet contents.
"""
from datetime import datetime
import socket
import struct

MAX_QUOTES_PER_MESSAGE = 50
MICROS_PER_SECOND = 1_000_000


def deserialize_price(x: bytes) -> float:
    """
    Convert a byte array used in the price feed messages to a floating point value

    :param x: bytestream to be converted
    :return: numeric representation of the price
    """
    return struct.unpack("f", x)[0]


def serialize_address(hostname: str, port: int) -> bytes:
    """
    Convert the subscriber's listening address into a byte stream

    :param hostname: subscriber's listening hostname/IP address
    :param port: subscriber's listening port number
    :return: 6-byte sequence in subscription request
    """
    host = socket.gethostbyname(hostname)  # To make sure that the function can handle 'google.com' or 'localhost'
    ipaddress_in_bytes = socket.inet_aton(host)
    port_number_in_bytes = port.to_bytes(length=2, byteorder='big')
    return ipaddress_in_bytes + port_number_in_bytes


def deserialize_utcdatetime(x: bytes) -> datetime:
    """
    Convert a byte stream from a Forex Provider message into a UTC datetime object

    :param x: 8-byte stream received in a big-endian network format
    :return: UTC compliant timestamp
    """
    padded_bytes = x.ljust(8, b'\x00')
    microseconds_since_epoch = struct.unpack('>Q', padded_bytes)[0]
    seconds = microseconds_since_epoch / MICROS_PER_SECOND
    return datetime.utcfromtimestamp(seconds)


def unmarshal_message(byte_sequence: bytes) -> list:
    """
    Construct the quote_sequence for a message from the given byte stream

    :param byte_sequence: byte stream received via UDP message
    :return: list of quote structures ('cross' and 'price', may also have 'timestamp')
    """
    quotes = list()

    for byte_section in range(0, len(byte_sequence), 32):
        currency_code = byte_sequence[byte_section: byte_section + 6].decode('ascii').replace('\x00', '/')
        exchange_rate = deserialize_price(byte_sequence[byte_section + 6: byte_section + 10])
        time = deserialize_utcdatetime(byte_sequence[byte_section + 10: byte_section + 18])
        quotes.append({'cross': currency_code, 'price': exchange_rate, 'timestamp': time})
    return quotes
