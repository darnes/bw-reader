import struct
from collections import namedtuple

import logging

_log = logging.getLogger(__name__)


def convert_data_stream(input_stream):
    """
    only one public function, input stream is passed, and ThinkGearPacket object instances are generated.
    :param stream:
    :return:
    """
    for data_portion in extract_data(input_stream):
        for packet in extract_packets(data_portion):
            yield translate_packet(*packet)


def check_sum(packet):
    """
    calculate checksum with respect to documentation,  as invert lowest 8 bits of the checksum accumulator.

    :param packet: data packet
    :return: checksum
    """
    return ~sum(ord(c) for c in packet) & 0xff


class ReadBuffer(object):
    def __init__(self, source, read_size=1024, max_len=4096):
        super(ReadBuffer, self).__init__()
        self._read_size = read_size
        self._max_len = max_len #not in use currently
        self._cache = ''
        self._source = source

    def read(self, n):
        while len(self._cache) < n:
            self._read_portion()
        ret_data = self._cache[0:n]
        self._cache = self._cache[n:]
        return ret_data

    def _read_portion(self):
        keep_reading = True
        while keep_reading:
            data_block = self._source.read(self._read_size)
            _log.debug('read size is %s', len(data_block))
            if len(data_block) < self._read_size:
                keep_reading = False
            self._cache += data_block
            _log.debug('cache size is %s', len(self._cache))



def extract_data(input_stream):
    """
    Extract data portions, and validates them before generate.

    :param input_stream: any stream - like object, that implements method read(n), where n is a number of bytes to read.
    :return: generator that produce valid data pieces
    """
    last_read = None
    keep_reading = True
    input_stream = ReadBuffer(input_stream)
    while keep_reading:
        current_read = input_stream.read(1)
        keep_reading = bool(current_read)
        if (last_read, current_read) == ('\xAA', '\xAA'):

            while current_read == '\xAA':
                current_read = input_stream.read(1)

            # trying to extract data
            packet_length = ord(current_read)
            if 170 > packet_length:
                # it's a length, doing magic
                data_portion = input_stream.read(packet_length)
                if check_sum(data_portion) == ord(input_stream.read(1)):
                    yield data_portion
            last_read = None
        else:
            last_read = current_read


def extract_packets(data_portion):
    """
    parses payload, as described in document.
    :param data_portion: data portion extracted with extract_data function
    :return: generator that yields data portions
    """
    while data_portion:
        ex_code_level = 0
        while data_portion and data_portion[0] == '\x55':
            ex_code_level += 1
            data_portion = data_portion[1:]

        # making sure there is nought data
        if len(data_portion) < 2:
            _log.warning('unexpectedly short package')
            break

        code = ord(data_portion[0])

        # meaning of after_code depends on  code value
        after_code = ord(data_portion[1])
        data_portion = data_portion[2:]

        if code >= 0x80:
            # after_code is a value len
            value = data_portion[0: after_code]
            data_portion = data_portion[after_code:]
            if len(value) < after_code:
                _log.warning('value len for multi-byte class less than %s', after_code)
                continue

        else:
            value = after_code
        #_log.debug('extracted data %s', (ex_code_level, code, value))
        yield ex_code_level, code, value


class ThinkGearPacket(object):
    code = 0
#    def __str__(self):
#        return '%s' % self.__class__.__name__


class TGSingleByteValue(ThinkGearPacket):
    min_val = 0
    max_val = 0

    def __init__(self, value):
        super(TGSingleByteValue, self).__init__()
        # TODO: make sense to check value ranges, but in fact they are used on rendering - so just ignoring for now
        self.value = value

    def __str__(self):
        return '{}:{}'.format(self.__class__.__name__, self.value)


class TGHeartRate(TGSingleByteValue):
    code = 0x3
    max_val = 255


class TGPoorSignal(TGSingleByteValue):
    code = 0x2
    max_val = 200


class TGAttentionESense(TGSingleByteValue):
    code = 0x4
    max_val = 100


class TGMeditationESense(TGSingleByteValue):
    code = 0x5
    max_val = 100


class TGBlinkStrength(TGSingleByteValue):
    code = 0x16
    max_val = 255

#done with single byte codes

class TGMultiByteValue(ThinkGearPacket):
    code = 0  # >= 0x80

    def __init__(self, value):
        self.value = self._decode(value)

    def _decode(self, value):
        raise NotImplementedError('This method need to be implemented in actual classes')


class TGRowDataValue(TGMultiByteValue):
    code = 0x80
    def _decode(self, value):
        """(-32768 to 32767)"""
        return struct.unpack('>h', value)[0]


EEGPowerData = namedtuple('EEGPowerData', ['delta', 'theta', 'low_alpha', 'high_alpha', 'low_beta',
                                           'high_beta', 'low_gamma', 'mid_gamma'])


class TGEEGPowerValue(TGMultiByteValue):
    code = 0x83
    max_val = 16777215
    def _decode(self, value):
        """tuple of unsigned longs, (0 to 16777215) """
        # data is 3 bytes unsigned integers, so using long
        return EEGPowerData(*struct.unpack('>8L', ''.join('\x00' + value[i:i + 3] for i in xrange(0, 24, 3))))


def translate_packet(ex_code_level, code, value):
    """

    :param ex_code_level: Extended Code Level(seems like out of use, but make sure on live testing)
    :param code: packet code
    :param value: packet value
    :return: ThinkGear packet instance.
    """
    code_to_class = {
        TGPoorSignal.code: TGPoorSignal,
        TGAttentionESense.code: TGAttentionESense,
        TGMeditationESense.code: TGMeditationESense,
        TGBlinkStrength.code: TGBlinkStrength,
        TGHeartRate.code: TGHeartRate,  # never seen so far with MindSet
        TGRowDataValue.code: TGRowDataValue,
        TGEEGPowerValue.code: TGEEGPowerValue
    }
    #if code == TGHeartRate.code:
    #    print 'got heart Rate!!!!' + '*' * 10
    if code in code_to_class:
        return code_to_class[code](value)
    else:
        _log.error('passed unknown code %s', code)

