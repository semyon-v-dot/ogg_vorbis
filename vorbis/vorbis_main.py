from typing import List

from .ogg import CorruptedFileDataError, FileDataException
from .decoders import (
    DataReader,
    AbstractDecoder,
    SetupHeaderDecoder,
    EndOfPacketException)


class PacketsProcessor(AbstractDecoder):
    """Class for processing packets of vorbis bitstream"""
    class LogicalStreamData:
        """Contains logical stream data"""
        # __init__

        byte_position: int

        # Identification header data

        audio_channels: int
        audio_sample_rate: int

        # From docs:
        # "The bitrate fields [...] are used only as hints. [...]
        # * All three fields set to the same value implies a fixed rate, or
        # tightly bounded, nearly fixed-rate bitstream
        # * Only nominal set implies a VBR or ABR stream that averages the
        # nominal bitrate
        # * Maximum and or minimum set implies a VBR bitstream that obeys the
        # bitrate limits
        # * None set indicates the encoder does not care to speculate"
        bitrate_maximum: int
        bitrate_nominal: int
        bitrate_minimum: int

        # Short window size
        blocksize_0: int
        # Long window size
        blocksize_1: int

        # Comment header data

        comment_header_decoding_failed: bool
        vendor_string: str
        user_comment_list_strings: List[str]

        # Setup header data

        vorbis_codebook_configurations: List['SetupHeaderDecoder.CodebookData']

        vorbis_floor_types: List[int]
        vorbis_floor_configurations: List['SetupHeaderDecoder.FloorData']

        vorbis_residue_types: List[int]
        vorbis_residue_configurations: List['SetupHeaderDecoder.ResidueData']

        vorbis_mapping_configurations: List['SetupHeaderDecoder.MappingData']

        vorbis_mode_configurations: List['SetupHeaderDecoder.ModeData']

        def __init__(self, input_byte_position: int):
            self.byte_position = input_byte_position

    _data_reader: DataReader
    _setup_header_decoder: SetupHeaderDecoder

    logical_stream: LogicalStreamData

    def __init__(self, filename: str):
        self._data_reader: DataReader = DataReader(filename)

        super().__init__(self._data_reader)

        self._basic_file_format_check(filename)

        self._setup_header_decoder = SetupHeaderDecoder(self._data_reader)

    def _basic_file_format_check(self, filename):
        """Method on a basic level checks if given file is ogg vorbis format"""
        try:
            for i in range(3):
                self._data_reader.read_packet()
                self._read_bytes(1)
                self._check_header_sync_pattern()
        except FileDataException:
            self.close_file()

            raise CorruptedFileDataError(
                "File format is not vorbis: " + filename)

        self._data_reader.restart_file_reading()

    def process_headers(self):
        """Method-wrapper for better debugging"""
        try:
            self._process_headers()
        except (FileDataException, BaseException) as occurred_exc:
            current_byte_position = (
                self._data_reader.get_packet_global_position()
                + self._data_reader.byte_pointer)

            occurred_exc.args += (
                'Error occurred on '
                f'[{current_byte_position}] byte position',)

            self.close_file()

            raise occurred_exc

    def _process_headers(self):
        """Processes headers in whole file creating [logical_stream] objects"""
        self._data_reader.read_packet()
        packet_type = self._read_bytes(1)

        self.logical_stream = self.LogicalStreamData(
            self._data_reader.get_packet_global_position())

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
        packet_type = self._read_bytes(1)
        if packet_type != b'\x03':
            raise CorruptedFileDataError('Comment header is lost')
        self.logical_stream.comment_header_decoding_failed = (
            False)
        try:
            self._process_comment_header()
        except EndOfPacketException:
            self.logical_stream.comment_header_decoding_failed = (
                True)

        self._data_reader.read_packet()
        packet_type = self._read_bytes(1)
        if packet_type != b'\x05':
            raise CorruptedFileDataError('Setup header is lost')
        try:
            self._process_setup_header()
        except EndOfPacketException:
            raise CorruptedFileDataError(
                'End of packet condition triggered while '
                'setup header decoding')

        try:
            while packet_type != b'\x01':
                self._data_reader.read_packet()
                packet_type = self._read_bytes(1)

            raise NotImplementedError(
                "Chained stream is not supported by this program")
        except EOFError:
            pass

    def _process_identification_header(self):
        """Processes identification header

        Stores info in appropriate [logical_stream] object from identification
        header"""
        self._check_header_sync_pattern()

        current_stream: 'PacketsProcessor.LogicalStreamData' = (
            self.logical_stream)

        vorbis_version = self._read_bits_for_int(32)

        current_stream.audio_channels = self._read_bits_for_int(8)
        current_stream.audio_sample_rate = self._read_bits_for_int(32)

        current_stream.bitrate_maximum = (
            self._read_bits_for_int(32, signed=True))
        current_stream.bitrate_nominal = (
            self._read_bits_for_int(32, signed=True))
        current_stream.bitrate_minimum = (
            self._read_bits_for_int(32, signed=True))

        current_stream.blocksize_0 = 1 << self._read_bits_for_int(4)
        current_stream.blocksize_1 = 1 << self._read_bits_for_int(4)

        framing_flag: int = self._read_bit()

        if vorbis_version != 0:
            raise CorruptedFileDataError('Version of Vorbis is zero')

        if (current_stream.audio_channels == 0
                or current_stream.audio_sample_rate == 0):
            raise CorruptedFileDataError(
                '[audio_channels] or [audio_sample_rate] equal to zero')

        # No checks for bitrate are needed because bitrate fields should be
        # used only as hints

        if current_stream.blocksize_0 > current_stream.blocksize_1:
            raise CorruptedFileDataError(
                '[blocksize_0] greater than [blocksize_1]')

        allowed_blocksizes = [64, 128, 256, 512, 1024, 2048, 4096, 8192]

        if (
                current_stream.blocksize_0 not in allowed_blocksizes
                or current_stream.blocksize_1 not in allowed_blocksizes):
            raise CorruptedFileDataError(
                '[blocksize_0] or [blocksize_1] have not allowed values')

        if framing_flag == 0:
            raise CorruptedFileDataError('Framing flag is a zero')

    def _process_comment_header(self):
        """Method process comment header storing info in appropriate \
[logical_stream] object"""
        self._check_header_sync_pattern()

        current_stream: 'PacketsProcessor.LogicalStreamData' = (
            self.logical_stream)

        vendor_length = self._read_bits_for_int(32)
        vendor_string = self._read_bytes(vendor_length)

        try:
            current_stream.vendor_string = \
                vendor_string.decode('utf-8')
        except UnicodeError:
            current_stream.comment_header_decoding_failed = True

        user_comment_list_length = self._read_bits_for_int(32)
        user_comment_list_strings = []

        for i in range(user_comment_list_length):
            length_ = self._read_bits_for_int(32)
            string_ = self._read_bytes(length_)

            try:
                user_comment_list_strings.append(string_.decode('utf-8'))
            except UnicodeError:
                current_stream.comment_header_decoding_failed = True
                user_comment_list_strings.append(
                    '[Unicode decoding failed]')

        current_stream.user_comment_list_strings = user_comment_list_strings

        if not bool(self._read_bit):  # framing bit
            current_stream.comment_header_decoding_failed = True

    def _process_setup_header(self):
        """Processes setup header info

        Stores info into current logical stream"""
        self._check_header_sync_pattern()

        current_stream = self.logical_stream

        # Codebooks decoding

        current_stream.vorbis_codebook_configurations = []

        for i in range(self._read_bits_for_int(8) + 1):
            current_stream.vorbis_codebook_configurations.append(
                self._setup_header_decoder.read_codebook())

        # Placeholders in Vorbis I

        vorbis_time_count = self._read_bits_for_int(6) + 1  # Line from docs

        for i in range(vorbis_time_count):
            placeholder = self._read_bits_for_int(16)

            if placeholder != 0:
                raise CorruptedFileDataError(
                    '[vorbis_time_count] placeholders contain nonzero')

        # Floors decoding
        (current_stream.vorbis_floor_types,
         current_stream.vorbis_floor_configurations) = (
            self._setup_header_decoder.read_floors(
                len(current_stream.vorbis_codebook_configurations)))

        # Residues decoding
        (current_stream.vorbis_residue_types,
         current_stream.vorbis_residue_configurations) = (
            self._setup_header_decoder.read_residues(
                current_stream.vorbis_codebook_configurations))

        # Mappings decoding
        current_stream.vorbis_mapping_configurations = (
            self._setup_header_decoder.read_mappings(
                current_stream.audio_channels,
                len(current_stream.vorbis_floor_types),
                len(current_stream.vorbis_residue_types)))

        # Modes decoding
        current_stream.vorbis_mode_configurations = (
            self._setup_header_decoder.read_modes(
                len(current_stream.vorbis_mapping_configurations)))

        # Framing bit check
        if self._read_bit() == 0:
            raise CorruptedFileDataError(
                'Framing bit lost while setup header decoding')

    def _check_header_sync_pattern(self):
        """Method checks if there is a header sync pattern in packet data"""
        pattern = self._read_bytes(6)

        if pattern != b'vorbis':
            raise CorruptedFileDataError(
                'Header sync pattern is absent')

    # WouldBeBetter: get_audio_data realisation
    # def get_audio_data(self):  # -> List[float]:
    #     """Returns list of PCM audio data from current audio packet
    #
    #     Raises EOFError on file end
    #     Raises EndOfPacketException. If so, current audio packet discards
    #     from stream
    #     """
    #     self._data_reader.read_packet()
    #
    #     if getattr(self, 'logical_stream', None) is None:
    #         raise ProgramException("Process file headers first")
    #
    #     packet_type: int = self._data_reader.read_bit()
    #
    #     if packet_type != 0:
    #         raise CorruptedFileDataError(
    #             'Got wrong packet type in process of audio data reading')
    #
    #     mode_number: int = self._data_reader.read_bits_for_int(
    #         ilog(len(self.logical_stream.vorbis_mode_configurations) - 1))
    #     n: int  # blocksize
    #     vorbis_mode_blockflag: int = (
    #         self.logical_stream
    #             .vorbis_mode_configurations[mode_number]
    #             .vorbis_mode_blockflag)
    #
    #     if vorbis_mode_blockflag == 0:
    #         n = self.logical_stream.blocksize_0
    #     else:
    #         n = self.logical_stream.blocksize_1
    #
    #     previous_window_flag: Optional[int] = None
    #     next_window_flag: Optional[int] = None
    #
    #     if vorbis_mode_blockflag == 1:
    #         previous_window_flag = self._data_reader.read_bit()
    #         next_window_flag = self._data_reader.read_bit()
    #
    #     # WouldBeBetter: Understand text below
    #     # From docs:
    #     # '''
    #     # if [previous_window_flag] is not set, the left half of the
    #     # window will be a hybrid window for lapping with a short block.
    #     # See paragraph 1.3.2, “Window shape decode (long windows only)”
    #     # for an illustration of overlapping dissimilar windows. Else, the
    #     # left half window will have normal long shape.
    #     #
    #     # if [next_window_flag] is not set, the right half of the window
    #     # will be a hybrid window for lapping with a short block. See
    #     # paragraph 1.3.2, “Window shape decode (long windows only)” for
    #     # an illustration of overlapping dissimilar windows. Else, the
    #     # left right window will have normal long shape.
    #     # '''
    #
    #     # These vars are integer because they are indexes in 'window' vector
    #     window_center: int = n//2
    #     left_window_start: int
    #     left_window_end: int
    #     left_n: int
    #     right_window_start: int
    #     right_window_end: int
    #     right_n: int
    #
    #     if vorbis_mode_blockflag == 1 and previous_window_flag == 0:
    #         left_window_start = n//4 - self.logical_stream.blocksize_0//4
    #         left_window_end = n//4 + self.logical_stream.blocksize_0//4
    #         left_n = self.logical_stream.blocksize_0//2
    #     else:
    #         left_window_start = 0
    #         left_window_end = window_center
    #         left_n = n//2
    #
    #     if vorbis_mode_blockflag == 1 and next_window_flag == 0:
    #         right_window_start = n*3//4 - self.logical_stream.blocksize_0//4
    #         right_window_end = n*3//4 + self.logical_stream.blocksize_0//4
    #         right_n = self.logical_stream.blocksize_0 // 2
    #     else:
    #         right_window_start = window_center
    #         right_window_end = n
    #         right_n = n // 2
    #
    #     window: List[float] = []
    #
    #     for i in range(left_window_start):
    #         window.append(0)
    #
    #     for i in range(left_window_start, left_window_end):
    #         window.append(
    #             sin(pi/2 * (
    #                 sin((i - left_window_start + 0.5) / left_n * pi/2)**2)))
    #
    #     for i in range(left_window_end, right_window_start):
    #         window.append(1)
    #
    #     for i in range(right_window_start, right_window_end):
    #         window.append(
    #             sin(pi/2 * (
    #                 sin(
    #                     (i - right_window_start + 0.5) /
    #                     right_n * pi/2 + pi/2)**2)))
    #
    #     for i in range(right_window_start, n):
    #         window.append(0)
    #
    #     try:
    #         current_mode_data: SetupHeaderDecoder.ModeData = (
    #             self.logical_stream
    #                 .vorbis_mode_configurations[mode_number])
    #         current_mapping_data: SetupHeaderDecoder.MappingData = (
    #             self.logical_stream
    #                 .vorbis_mapping_configurations[
    #                     current_mode_data.vorbis_mode_mapping])
    #
    #         # Floor info for every audio channel
    #         # floor_info: List = []
    #         # 'True' if floor info decode returned 'unused'
    #         # and 'False' otherwise
    #         # no_residue: List[bool] = []
    #
    #         for i in range(self.logical_stream.audio_channels):
    #             submap_number: int = (
    #                 current_mapping_data.vorbis_mapping_mux[i])
    #             floor_number: int = (
    #                 current_mapping_data.vorbis_mapping_submap_floor[
    #                     submap_number])
    #
    #             if floor_number == 0:
    #                 raise CorruptedFileDataError(
    #                     "Got floor type 0 when decoding audio data. This "
    #                     "program DO NOT support any floor 0 decoding!")
    #
    #             if floor_number == 1:
    #                 self._audio_data_decoder.floor_type_1_packet_decode()
    #                 # WouldBeBetter: Stopped here
    #
    #     except EndOfPacketException:
    #         pass

    def close_file(self):
        """Method closes opened ogg-vorbis file"""
        self._data_reader.close_file()
