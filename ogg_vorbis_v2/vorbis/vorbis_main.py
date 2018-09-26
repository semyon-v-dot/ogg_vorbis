from .ogg import PacketsReader
from .helper_funcs import *
from .codebook import CodebookDecoder
from .errors import *


class EndOfPacketError(Exception):
    '''Raised when end-of-packet condition triggered'''
    pass


class IncorrectVariablesValuesError(Exception):
    '''Raised when decoded values of some variables are incorrect'''
    def __init__(self,
                 variable_names, variable_values,
                 why_incorrect, number_of_logical_stream):
        pass


class DataReader:
    '''Class for low-level data reading'''
    def __init__(self, filename):
        self._packets_reader = PacketsReader(filename)
        self._current_packet = b''
        self.byte_pointer = 0
        self.bit_pointer = 0

    def restart_file_reading(self):
        '''Method resets file and packet pointers as at the start of the file \
reading'''
        self.set_global_position(0)
        self._current_packet = b''
        self.byte_pointer = 0
        self.bit_pointer = 0

    def set_global_position(self, new_position):
        '''Method moves global position of [byte_pointer] in audiofile'''
        self._packets_reader.move_byte_pointer(new_position)

    def get_global_position(self):
        '''Method returns global position of [byte_pointer] in audiofile'''
        return self._packets_reader.byte_pointer

    def read_packet(self):
        '''Method reads packet from [packets_reader]'''
        self._current_packet = self._packets_reader.read_packet()[0]
        self.byte_pointer = self.bit_pointer = 0

    def read_bit(self):
        '''Method reads and return one bit from current packet data'''
        try:
            required_bit = bool(self._current_packet[self.byte_pointer] &
                                (1 << self.bit_pointer))
        except IndexError:
            raise EndOfPacketError('End of packet condition triggered')

        self.bit_pointer += 1
        if self.bit_pointer == 8:
            self.bit_pointer = 0
            self.byte_pointer += 1

        return int(required_bit)

    def read_byte(self):
        '''Method reads and return one byte from current packet'''
        return bytes([self.read_bits_for_int(8)])

    def read_bits_for_int(self, bits_count, signed=False):
        '''Method reads [bits_count] bits from current packet and return \
unsigned int value'''
        if bits_count <= 0:
            raise ValueError('Count of bits for reading int '
                             'is less than zero')

        number = ''
        for i in range(bits_count):
            number = str(self.read_bit()) + number

        if not signed or number[0] == '0':
            return int(number, 2)
        else:
            number = int(number, 2) - 1
            return -(number ^
                     int(''.join(['1' for i in range(bits_count)]), 2))


class PacketsProcessor:
    '''Class for processing packets of vorbis bitstream'''
    def __init__(self, filename):
        self._data_reader = DataReader(filename)
        self._read_bit = self._data_reader.read_bit
        self._read_byte = self._data_reader.read_byte
        self._read_bits_for_int = self._data_reader.read_bits_for_int

        self._basic_file_format_check(filename)

        self._codebook_decoder = CodebookDecoder(self._data_reader)

        self.logical_streams = []

    def _basic_file_format_check(self, filename):
        '''Method on a basic level checks if given file is ogg vorbis format'''
        try:
            for i in range(3):
                self._data_reader.read_packet()
                self._read_byte()
                self._check_header_sync_pattern()
        except (SystemExit, EndOfPacketError):
            print("File format is not vorbis: " + filename)
            exit(ERROR_FILE_FORMAT_NOT_VORBIS)

        self._data_reader.restart_file_reading()

# headers processing

    class LogicalStream:
        '''Class represents one logical stream info'''
        # # # __init__:
        #
        # byte_position
        #
        # # # Identification header:
        #
        # audio_channels
        # audio_sample_rate
        # bitrate_maximum
        # bitrate_nominal
        # bitrate_minimum
        # blocksize_0
        # blocksize_1
        #
        # # # Comment header:
        #
        # comment_header_decoding_failed
        # vendor_string
        # user_comment_list_strings
        #
        # # # Setup header:
        #
        # vorbis_codebook_configurations
        #   # [(codebook_1, VQ_lookup_table_1), ...]
        # ...
        def __init__(self, byte_position):
            self.byte_position = byte_position

    def _check_header_sync_pattern(self):
        '''Method checks if there is a header sync pattern in packet data'''
        pattern = b''
        for i in range(6):
            pattern += self._read_byte()

        if pattern != b'\x76\x6f\x72\x62\x69\x73':
            print('Header sync pattern is absent')
            exit(ERROR_HEADER_SYNC_PATTERN_IS_ABSENT)

    def _process_identification_header(self):  # tests
        '''Method process identification header storing info in appropriate \
[logical_stream] object'''
        self._check_header_sync_pattern()

        vorbis_version = self._read_bits_for_int(32)
        if vorbis_version != 0:
            why_incorrect = 'Decoder is not compatible '\
                            'with this version of Vorbis'
            raise IncorrectVariablesValuesError(
                'vorbis_version',
                vorbis_version,
                why_incorrect,
                len(self.logical_streams))

        self.logical_streams[-1].audio_channels = self._read_bits_for_int(8)
        self.logical_streams[-1].audio_sample_rate =\
            self._read_bits_for_int(32)
        if self.logical_streams[-1].audio_channels == 0 or\
           self.logical_streams[-1].audio_sample_rate == 0:
            why_incorrect = 'Amount of audio channels or audio sample rate'\
                            'equal to zero'
            raise IncorrectVariablesValuesError(
                ('audio_channels', 'audio_sample_rate'),
                (self.logical_streams[-1].audio_channels,
                 self.logical_streams[-1].audio_sample_rate),
                why_incorrect,
                len(self.logical_streams))

        self.logical_streams[-1].bitrate_maximum =\
            self._read_bits_for_int(32, signed=True)
        self.logical_streams[-1].bitrate_nominal =\
            self._read_bits_for_int(32, signed=True)
        self.logical_streams[-1].bitrate_minimum =\
            self._read_bits_for_int(32, signed=True)

        self.logical_streams[-1].blocksize_0 = self._read_bits_for_int(4)
        self.logical_streams[-1].blocksize_1 = self._read_bits_for_int(4)
        allowed_blocksizes = [64, 128, 256, 512, 1024, 2048, 4096, 8192]
        if self.logical_streams[-1].blocksize_0 >\
           self.logical_streams[-1].blocksize_1:
            why_incorrect = '[blocksize_0] greater than [blocksize_1]'
            raise IncorrectVariablesValuesError(
                ('blocksize_0', 'blocksize_1'),
                (self.logical_streams[-1].blocksize_0,
                 self.logical_streams[-1].blocksize_1),
                why_incorrect,
                len(self.logical_streams))
        if (1 << self.logical_streams[-1].blocksize_0) not in \
           allowed_blocksizes or \
           (1 << self.logical_streams[-1].blocksize_1) not in \
           allowed_blocksizes:
            why_incorrect = '[blocksize_0] or [blocksize_1] have not allowed '\
                            'values'
            raise IncorrectVariablesValuesError(
                ('blocksize_0', 'blocksize_1'),
                (self.logical_streams[-1].blocksize_0,
                 self.logical_streams[-1].blocksize_1),
                why_incorrect,
                len(self.logical_streams))

        if not self._read_bit():
            raise ValueError('Framing flag is a zero while reading '
                             'identification header')

    def _process_comment_header(self):  # tests
        '''Method process comment header storing info in appropriate \
[logical_stream] object'''
        self._check_header_sync_pattern()

        vendor_length = self._read_bits_for_int(32)
        vendor_string = b''
        for i in range(vendor_length):
            vendor_string += self._read_byte()
        self.logical_streams[-1].vendor_string = vendor_string.decode('utf-8')

        user_comment_list_length = self._read_bits_for_int(32)
        user_comment_list_strings = []
        for i in range(user_comment_list_length):
            length_ = self._read_bits_for_int(32)
            string_ = b''
            for i in range(length_):
                string_ += self._read_byte()
            user_comment_list_strings += [string_.decode('utf-8')]
        self.logical_streams[-1].user_comment_list_strings = \
            user_comment_list_strings

        if not self._read_bit:  # framing bit
            self.logical_streams[-1].comment_header_decoding_failed = True

    def _process_setup_header(self):  # WIP
        '''Method process setup header storing info in appropriate \
[logical_stream] object'''
        self._check_header_sync_pattern()

        vorbis_codebook_count = self._read_bits_for_int(8) + 1
        self.logical_streams[-1].vorbis_codebook_configurations = []
        for i in range(vorbis_codebook_count):
            self.logical_streams[-1].vorbis_codebook_configurations +=\
                [self._codebook_decoder.read_codebook()]

        vorbis_time_count = self._read_bits_for_int(6) + 1
        for i in range(vorbis_time_count):
            placeholder = self._read_bits_for_int(16)
            if placeholder != 0:
                raise ValueError('[vorbis_time_count] placeholders '
                                 'are contain nonzero value. Number: ' +
                                 str(i))

        vorbis_floor_count = self._read_bits_for_int(6) + 1
        vorbis_floor_types = []
        # for i in range(vorbis_floor_count):
        #     vorbis_floor_types += [self._read_bits_for_int(16)]

    def process_headers(self):
        '''Method process headers in whole file creating [logical_stream] \
objects'''
        try:
            self._data_reader.read_packet()
            packet_type = self._read_byte()
            while True:
                self.logical_streams += [self.LogicalStream(
                    self._data_reader.get_global_position())]
                if packet_type != b'\x01':
                    print('Identification header is lost')
                    exit(ERROR_IDENTIFICATION_HEADER_IS_LOST)
                self._process_identification_header()

                self._data_reader.read_packet()
                packet_type = self._read_byte()
                if packet_type != b'\x03':
                    print('Comment header is lost')
                    exit(ERROR_COMMENT_HEADER_IS_LOST)
                self.logical_streams[-1].comment_header_decoding_failed = \
                    False
                try:
                    self._process_comment_header()
                except EndOfPacketError:
                    self.logical_streams[-1].comment_header_decoding_failed =\
                        True

                self._data_reader.read_packet()
                packet_type = self._read_byte()
                if packet_type != b'\x05':
                    print('Setup header is lost')
                    exit(ERROR_SETUP_HEADER_IS_LOST)
                self._process_setup_header()

                while packet_type != b'\x01':
                    self._data_reader.read_packet()
                    packet_type = self._read_byte()
        except EOFError:
            self._data_reader.restart_file_reading()
