from typing import List, Tuple

from .ogg import CorruptedFileDataError, FileDataException
from .decoders import (
    DataReader,
    AbstractDecoder,
    CodebookDecoder,
    FloorDecoder,
    ResidueDecoder,
    MappingDecoder,
    EndOfPacketException)


class PacketsProcessor(AbstractDecoder):
    """Class for processing packets of vorbis bitstream"""
    class LogicalStream:
        """Contains logical stream info"""
        # __init__

        byte_position: int

        # Identification header data

        audio_channels: int
        audio_sample_rate: int
        bitrate_maximum: int
        bitrate_nominal: int
        bitrate_minimum: int
        blocksize_0: int
        blocksize_1: int

        # Comment header data

        comment_header_decoding_failed: bool
        vendor_string: str
        user_comment_list_strings: List[str]

        # Setup header data

        vorbis_codebook_configurations: List[CodebookDecoder.CodebookData] = []

        # TODO: Should decoder return types?
        vorbis_floor_types: List[int] = []
        vorbis_floor_configurations: List[FloorDecoder.FloorData] = []

        # TODO: Should decoder return types?
        vorbis_residue_types: List[int]
        vorbis_residue_configurations: List[ResidueDecoder.ResidueData] = []

        vorbis_mapping_configurations: List[MappingDecoder.MappingData] = []

        vorbis_mode_configurations: Tuple[int, int] = []

        def __init__(self, input_byte_position: int):
            self.byte_position = input_byte_position

    _codebook_decoder: CodebookDecoder
    _floors_decoder: FloorDecoder

    logical_streams: List[LogicalStream] = []

    def __init__(self, filename: str):
        self._data_reader: DataReader = DataReader(filename)

        super().__init__(self._data_reader)

        self._basic_file_format_check(filename)

        self._codebook_decoder = CodebookDecoder(self._data_reader)
        self._floors_decoder = FloorDecoder(self._data_reader)

    def _basic_file_format_check(self, filename):
        """Method on a basic level checks if given file is ogg vorbis format"""
        try:
            for i in range(3):
                self._data_reader.read_packet()
                self._read_byte()
                self._check_header_sync_pattern()
        except EndOfPacketException:
            raise CorruptedFileDataError(
                "File format is not vorbis: " + filename)

        self._data_reader.restart_file_reading()

    def process_headers(self):
        """Method-wrapper for better exception debugging"""
        try:
            self._process_headers()
        except (FileDataException, BaseException) as occurred_exc:
            occurred_exc.args += (
                f'\nError occurred in [{len(self.logical_streams)}] '
                'logical stream',
                '\nError occurred on '
                f'[{self._data_reader.get_global_position()}] '
                'byte position'
            )
            raise occurred_exc

    def _process_headers(self):
        """Processes headers in whole file creating [logical_stream] objects"""
        try:
            self._data_reader.read_packet()
            packet_type = self._read_byte()
            while True:
                self.logical_streams.append(self.LogicalStream(
                    self._data_reader.get_global_position()))
                if packet_type != b'\x01':
                    raise CorruptedFileDataError(
                        'Identification header is lost')
                try:
                    self._process_identification_header()
                except EndOfPacketException:
                    raise CorruptedFileDataError(
                        'End of packet condition triggered while '
                        'identification header decoding')

                self._data_reader.read_packet()
                packet_type = self._read_byte()
                if packet_type != b'\x03':
                    raise CorruptedFileDataError('Comment header is lost')
                self.logical_streams[-1].comment_header_decoding_failed = (
                    False)
                try:
                    self._process_comment_header()
                except EndOfPacketException:
                    self.logical_streams[-1].comment_header_decoding_failed = (
                        True)

                self._data_reader.read_packet()
                packet_type = self._read_byte()
                if packet_type != b'\x05':
                    raise CorruptedFileDataError('Setup header is lost')
                try:
                    self._process_setup_header()
                except EndOfPacketException:
                    raise CorruptedFileDataError(
                        'End of packet condition triggered while '
                        'setup header decoding')

                while packet_type != b'\x01':
                    self._data_reader.read_packet()
                    packet_type = self._read_byte()
        except EOFError:
            self._data_reader.restart_file_reading()

    # TODO
    def _process_setup_header(self):
        """Processes setup header info

        Stores info into current logical stream"""
        self._check_header_sync_pattern()
        current_stream = self.logical_streams[-1]

        # Codebooks decoding
        for i in range(self._read_bits_for_int(8) + 1):
            current_stream.vorbis_codebook_configurations.append(
                self._codebook_decoder.read_codebook())

        # Placeholders in Vorbis I
        vorbis_time_count = self._read_bits_for_int(6) + 1  # Line from docs
        for i in range(vorbis_time_count):
            placeholder = self._read_bits_for_int(16)
            if placeholder != 0:
                raise CorruptedFileDataError(
                    '[vorbis_time_count] placeholders '
                    'are contain nonzero value. Number: '
                    + str(i))

        # Floors decoding
        for i in range(self._read_bits_for_int(6) + 1):
            current_stream.vorbis_floor_types.append(
                self._read_bits_for_int(16))

            if current_stream.vorbis_floor_types[i] == 1:
                current_stream.vorbis_floor_configurations.append(
                    self._floors_decoder.decode_floor_config_type_1())

            elif current_stream.vorbis_floor_types[i] == 0:
                current_stream.vorbis_floor_configurations.append(
                    self._floors_decoder.decode_floor_config_type_0())

            else:
                raise CorruptedFileDataError(
                    'Not supported floor type: '
                    + str(current_stream.vorbis_floor_types[i]))

        # current_stream.vorbis_residue_configurations = (
        #     self._residue_decoder._process_residues())
        #
        # current_stream.vorbis_mapping_configurations = (
        #     self._mapping_decoder._process_mappings())
        #
        # self._process_modes()

    # TODO
    def _process_modes(self):
        """Processes modes of current logical stream

        Some info about modes.
        The mode mechanism is used to encode a frame according to one of
        multiple possible methods with the intention of choosing a method best
        suited to that frame. Different modes are, e.g. how frame size is
        changed from frame to frame. The mode number of a frame serves as a
        top level configuration switch for all other specific aspects of frame
        decode"""
        # vorbis_mode_count = self._read_bits_for_int(6) + 1
        # current_stream.vorbis_mode_configurations = []
        # for i in range(vorbis_mode_count):
        #     vorbis_mode_blockflag = self._read_bit()
        #     vorbis_mode_windowtype = self._read_bits_for_int(16)
        #     vorbis_mode_transformtype = self._read_bits_for_int(16)
        #     vorbis_mode_mapping = self._read_bits_for_int(8)
        #     if (vorbis_mode_windowtype != 0
        #             or vorbis_mode_transformtype != 0):
        #         raise CorruptedFileDataError(
        #             'Received incorrect [vorbis_mode_windowtype] or '
        #             '[vorbis_mode_transformtype] or [vorbis_mode_mapping]: '
        #             + str(vorbis_mode_windowtype) + ' '
        #             + str(vorbis_mode_transformtype))
        #     if (vorbis_mode_mapping
        #             > len(current_stream.vorbis_mapping_configurations)):
        #         raise CorruptedFileDataError(
        #             'Received incorrect [vorbis_mode_mapping]: '
        #             + str(vorbis_mode_mapping))
        #
        #     current_stream.vorbis_mode_configurations.append(
        #         (vorbis_mode_blockflag, vorbis_mode_mapping))
        #
        # if not self._read_bit():
        #     raise CorruptedFileDataError(
        #         'Framing bit lost while setup header decoding')
        pass

    def _process_identification_header(self):
        """Processes identification header

        Stores info in appropriate [logical_stream] object from identification
        header"""
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

    def _process_comment_header(self):
        """Method process comment header storing info in appropriate \
[logical_stream] object"""
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

    def _check_header_sync_pattern(self):
        """Method checks if there is a header sync pattern in packet data"""
        pattern = self._read_bytes(6)

        if pattern != b'\x76\x6f\x72\x62\x69\x73':
            raise CorruptedFileDataError(
                'Header sync pattern is absent')

    def close_file(self):
        """Method closes opened ogg-vorbis file"""
        self._data_reader.close_file()
