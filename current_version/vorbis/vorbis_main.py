from .ogg import PacketsReader, CorruptedFileDataError
from .codebook import CodebookDecoder


class FileNotVorbisError(Exception):
    '''Raise when given file has not vorbis format'''
    pass


class EndOfPacketError(Exception):
    '''Raised when end-of-packet condition triggered'''
    pass


class DataReader:
    '''Class for low-level data reading'''
    def __init__(self, filename):
        self._packets_reader = PacketsReader(filename)
        self._current_packet = b''
        self.byte_pointer = 0
        self.bit_pointer = 0

    def close_file(self):
        '''Method closes opened ogg-vorbis file'''
        self._packets_reader.close_file()

# working with global reading position

    def restart_file_reading(self):
        '''Method resets file and packet pointers as at the start of the file \
reading'''
        self.set_global_position(0)
        self._current_packet = b''
        self.byte_pointer = 0
        self.bit_pointer = 0

    def set_global_position(self, new_position):
        '''Method moves global position of [byte_pointer] in audiofile'''
        self._packets_reader.move_byte_position(new_position)

    def get_global_position(self):
        '''Method returns global position of [byte_pointer] in audiofile'''
        return self._packets_reader.opened_file.tell()

# basic level reading

    def read_packet(self):
        '''Method reads packet from [packets_reader]'''
        self._current_packet = self._packets_reader.read_packet()[0]
        self.byte_pointer = self.bit_pointer = 0

    def read_bit(self):
        '''Method reads and return one bit from current packet data'''
        try:
            required_bit = bool(self._current_packet[self.byte_pointer]
                                & (1 << self.bit_pointer))
        except IndexError:
            raise EndOfPacketError('End of packet condition triggered')

        self.bit_pointer += 1
        if self.bit_pointer == 8:
            self.bit_pointer = 0
            self.byte_pointer += 1

        return int(required_bit)

    def read_bits(self, bits_count):
        '''Method reads and return several bits from current packet data'''
        assert bits_count >= 0

        readed_bits = ''
        for i in range(bits_count):
            readed_bits = str(self.read_bit()) + readed_bits
        
        return readed_bits

    def read_byte(self):
        '''Method reads and return one byte from current packet'''
        return bytes([self.read_bits_for_int(8)])

    def read_bytes(self, bytes_count):
        '''Method reads and return several bytes from current packet'''
        assert bytes_count >= 0

        readed_bytes = b''
        for i in range(bytes_count):
            readed_bytes += self.read_byte()

        return readed_bytes

    def read_bits_for_int(self, bits_count, signed=False):
        '''Method reads [bits_count] bits from current packet and return \
unsigned int value'''
        assert bits_count >= 0

        number = self.read_bits(bits_count)

        if not signed or number[0] == '0':
            return int(number, 2)
        else:
            number = int(number, 2) - 1
            return -(number
                     ^ int(''.join(['1' for i in range(bits_count)]), 2))


class PacketsProcessor:
    '''Class for processing packets of vorbis bitstream'''
    def __init__(self, filename):
        self._data_reader = DataReader(filename)
        
        self._read_bit = self._data_reader.read_bit
        self._read_bits = self._data_reader.read_bits
        self._read_bits_for_int = self._data_reader.read_bits_for_int

        self._read_byte = self._data_reader.read_byte
        self._read_bytes = self._data_reader.read_bytes

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
        except EndOfPacketError:
            raise FileNotVorbisError(
                "File format is not vorbis: " + filename)

        self._data_reader.restart_file_reading()

    def close_file(self):
        '''Method closes opened ogg-vorbis file'''
        self._data_reader.close_file()

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
            assert byte_position >= 0

            self.byte_position = byte_position

    def _check_header_sync_pattern(self):
        '''Method checks if there is a header sync pattern in packet data'''
        pattern = self._read_bytes(6)

        if pattern != b'\x76\x6f\x72\x62\x69\x73':
            raise CorruptedFileDataError(
                'Header sync pattern is absent')

    def _process_identification_header(self):
        '''Method process identification header storing info in appropriate \
[logical_stream] object'''
        self._check_header_sync_pattern()
        
        logical_stream_info = (
            'Logical stream number: ' + str(len(self.logical_streams)))

        vorbis_version = self._read_bits_for_int(32)
        if vorbis_version != 0:
            raise CorruptedFileDataError(
                'Decoder is not compatible with this version of Vorbis. '
                + logical_stream_info)

        self.logical_streams[-1].audio_channels = self._read_bits_for_int(8)
        self.logical_streams[-1].audio_sample_rate =\
            self._read_bits_for_int(32)
        if self.logical_streams[-1].audio_channels == 0 or\
           self.logical_streams[-1].audio_sample_rate == 0:
            raise CorruptedFileDataError(
                'Amount of audio channels or audio sample rate'
                'equal to zero. '
                + logical_stream_info)

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
            raise CorruptedFileDataError(
                '[blocksize_0] greater than [blocksize_1]. '
                + logical_stream_info)
        if (1 << self.logical_streams[-1].blocksize_0) not in \
           allowed_blocksizes or \
           (1 << self.logical_streams[-1].blocksize_1) not in \
           allowed_blocksizes:
            raise CorruptedFileDataError(
                '[blocksize_0] or [blocksize_1] have not allowed values. '
                + logical_stream_info)

        if not self._read_bit():
            raise CorruptedFileDataError(
                'Framing flag is a zero while reading identification header. '
                + logical_stream_info)

    def _process_comment_header(self):  # tests?
        '''Method process comment header storing info in appropriate \
[logical_stream] object'''
        self._check_header_sync_pattern()

        vendor_length = self._read_bits_for_int(32)
        vendor_string = self._read_bytes(vendor_length)
        try:
            self.logical_streams[-1].vendor_string = \
                vendor_string.decode('utf-8')
        except UnicodeError:
            self.logical_streams[-1].comment_header_decoding_failed = True

        user_comment_list_length = self._read_bits_for_int(32)
        user_comment_list_strings = []
        for i in range(user_comment_list_length):
            length_ = self._read_bits_for_int(32)
            string_ = self._read_bytes(length_)
            try:
                user_comment_list_strings.append(string_.decode('utf-8'))
            except UnicodeError:
                self.logical_streams[-1].comment_header_decoding_failed = True
                user_comment_list_strings.append(
                    '[Unicode decoding failed]')
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
            self.logical_streams[-1].vorbis_codebook_configurations.append(
                self._codebook_decoder.read_codebook())

        vorbis_time_count = self._read_bits_for_int(6) + 1
        for i in range(vorbis_time_count):
            placeholder = self._read_bits_for_int(16)
            if placeholder != 0:
                raise CorruptedFileDataError(
                    '[vorbis_time_count] placeholders '
                    'are contain nonzero value. Number: '
                    + str(i))

        vorbis_floor_count = self._read_bits_for_int(6) + 1
        exit(str(vorbis_floor_count))
        vorbis_floor_types = []
        # for i in range(vorbis_floor_count):
        #     vorbis_floor_types.append(self._read_bits_for_int(16))

    def process_headers(self):
        '''Method process headers in whole file creating [logical_stream] \
objects'''
        try:
            self._data_reader.read_packet()
            packet_type = self._read_byte()
            while True:
                self.logical_streams.append(self.LogicalStream(
                    self._data_reader.get_global_position()))
                if packet_type != b'\x01':
                    raise CorruptedFileDataError(
                        'Identification header is lost')
                self._process_identification_header()

                self._data_reader.read_packet()
                packet_type = self._read_byte()
                if packet_type != b'\x03':
                    raise CorruptedFileDataError('Comment header is lost')
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
                    raise CorruptedFileDataError('Setup header is lost')
                self._process_setup_header()

                while packet_type != b'\x01':
                    self._data_reader.read_packet()
                    packet_type = self._read_byte()
        except EOFError:
            self._data_reader.restart_file_reading()
