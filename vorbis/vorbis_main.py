from dataclasses import dataclass
from typing import Optional, List

from .ogg import PacketsReader, CorruptedFileDataError
from .codebook import CodebookDecoder
from .helper_funcs import ilog


class EndOfPacketException(Exception):
    """Raised when end-of-packet condition triggered"""
    pass


class DataReader:
    """Class for low-level data reading"""
    _current_packet: bytes
    byte_pointer: int = 0
    bit_pointer: int = 0

    def __init__(self, filename: Optional[str] = None, data: bytes = b''):
        if filename is not None:
            self._packets_reader = PacketsReader(filename)
        self._current_packet = data

    def close_file(self):
        """Method closes opened ogg-vorbis file"""
        self._packets_reader.close_file()

    def restart_file_reading(self):
        """Resets file and packet pointers to zero"""
        self.set_global_position(0)
        self._current_packet = b''
        self.byte_pointer = 0
        self.bit_pointer = 0

    def set_global_position(self, new_position: int):
        """Method moves global position of [byte_pointer] in audio file"""
        self._packets_reader.move_byte_position(new_position)

    def get_global_position(self):
        """Method returns global position of [byte_pointer] in audio file"""
        return self._packets_reader.opened_file.tell()

    def read_packet(self):
        """Method reads packet from [packets_reader]"""
        self._current_packet = self._packets_reader.read_packet()[0]
        self.byte_pointer = self.bit_pointer = 0

    def read_bit(self) -> int:
        """Method reads and return one bit from current packet data"""
        try:
            required_bit = bool(self._current_packet[self.byte_pointer]
                                & (1 << self.bit_pointer))
        except IndexError:
            raise EndOfPacketException('End of packet condition triggered')

        self.bit_pointer += 1
        if self.bit_pointer == 8:
            self.bit_pointer = 0
            self.byte_pointer += 1

        return int(required_bit)

    def read_bits(self, bits_count: int) -> str:
        """Method reads and return several bits from current packet data"""
        assert bits_count >= 0

        read_bits = ''
        for i in range(bits_count):
            read_bits = str(self.read_bit()) + read_bits

        return read_bits

    def read_byte(self) -> bytes:
        """Method reads and return one byte from current packet"""
        return bytes([self.read_bits_for_int(8)])

    def read_bytes(self, bytes_count: int) -> bytes:
        """Method reads and return several bytes from current packet"""
        assert bytes_count >= 0

        read_bytes = b''
        for i in range(bytes_count):
            read_bytes += self.read_byte()

        return read_bytes

    def read_bits_for_int(self, bits_count: int, signed: bool = False) -> int:
        """Reads bits from current packet for int value

        Reads [bits_count] bits from current packet and return unsigned int
        value"""
        assert bits_count >= 0

        number = self.read_bits(bits_count)

        if not signed or number[0] == '0':
            return int(number, 2)
        else:
            number = int(number, 2) - 1
            return -(number
                     ^ int(''.join(['1'] * bits_count), 2))


class PacketsProcessor:
    """Class for processing packets of vorbis bitstream"""
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

    def close_file(self):
        """Method closes opened ogg-vorbis file"""
        self._data_reader.close_file()

# headers processing

    @dataclass
    class LogicalStream:
        """Contains logical stream info"""
        # __init__
        byte_position: int

        # Identification header
        audio_channels: Optional[int] = None
        audio_sample_rate: Optional[int] = None
        bitrate_maximum: Optional[int] = None
        bitrate_nominal: Optional[int] = None
        bitrate_minimum: Optional[int] = None
        blocksize_0: Optional[int] = None
        blocksize_1: Optional[int] = None

        # Comment header
        comment_header_decoding_failed: Optional[bool] = None
        vendor_string: Optional[str] = None
        user_comment_list_strings: Optional[List[str]] = None

        # Setup header
        # vorbis_codebook_configurations # TODO: Type
        vorbis_floor_types: Optional[List[int]] = None
        # vorbis_floor_configurations # TODO: Type
        vorbis_residue_types: Optional[List[int]] = None
        # vorbis_residue_configurations # TODO: Type
        # vorbis_mapping_configurations # TODO: Type
        # vorbis_mode_configurations # TODO: Type

    def _check_header_sync_pattern(self):
        """Method checks if there is a header sync pattern in packet data"""
        pattern = self._read_bytes(6)

        if pattern != b'\x76\x6f\x72\x62\x69\x73':
            raise CorruptedFileDataError(
                'Header sync pattern is absent')

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

    # floor decoding # start

    @dataclass
    class FloorData:
        """Class for storing floor data"""
        floor1_partition_class_list: list
        floor1_class_dimensions: list
        floor1_class_subclasses: list
        floor1_class_masterbooks: list
        floor1_subclass_books: list
        floor1_multiplier: int
        floor1_X_list: list

    def _decode_floor_config_type_1(self):
        """Method decodes floor configuration type 1"""
        current_stream = self.logical_streams[-1]

        floor1_partitions = self._read_bits_for_int(5)
        maximum_class = -1
        floor1_partition_class_list = []

        for i in range(floor1_partitions):
            floor1_partition_class_list.append(
                self._read_bits_for_int(4))

        maximum_class = max(floor1_partition_class_list)
        floor1_class_dimensions = []
        floor1_class_subclasses = []
        floor1_class_masterbooks = []
        floor1_subclass_books = []
        for i in range(maximum_class + 1):
            floor1_class_dimensions.append(self._read_bits_for_int(3) + 1)
            floor1_class_subclasses.append(self._read_bits_for_int(2))
            if floor1_class_subclasses[i] != 0:
                floor1_class_masterbooks.append(self._read_bits_for_int(8))
                if (floor1_class_masterbooks[i]
                        > len(current_stream.vorbis_codebook_configurations)):
                    raise CorruptedFileDataError(
                        'Received incorrect [floor1_class_masterbooks] '
                        'item while floor config decoding: '
                        + str(floor1_class_masterbooks[i]))
            else:
                floor1_class_masterbooks.append(-1)

            floor1_subclass_books.append([])
            for j in range(1 << floor1_class_subclasses[i]):
                floor1_subclass_books[i].append(self._read_bits_for_int(8) - 1)
                if (floor1_subclass_books[i][j]
                        > len(current_stream.vorbis_codebook_configurations)):
                    raise CorruptedFileDataError(
                        'Received incorrect [floor1_subclass_books] '
                        'item while floor config decoding: '
                        + str(floor1_subclass_books[i]))

        floor1_multiplier = self._read_bits_for_int(2) + 1
        range_bits = self._read_bits_for_int(4)
        floor1_x_list = [0, 1 << range_bits]
        # floor1_values = 2
        for i in range(floor1_partitions):
            current_class_number = floor1_partition_class_list[i]

            for j in range(floor1_class_dimensions[current_class_number]):
                floor1_x_list.append(
                    self._read_bits_for_int(range_bits))
                # floor1_values += 1
        if len(floor1_x_list) > 65:
            raise CorruptedFileDataError(
                '[floor1_X_list] have more than 65 elements while floor '
                'config decoding')
        if len(floor1_x_list) != len(set(floor1_x_list)):
            raise CorruptedFileDataError(
                '[floor1_X_list] have non unique elements while floor '
                'config decoding: ' + str(floor1_x_list))

        return self.FloorData(
            floor1_partition_class_list,
            floor1_class_dimensions,
            floor1_class_subclasses,
            floor1_class_masterbooks,
            floor1_subclass_books,
            floor1_multiplier,
            floor1_x_list)

    def _decode_floor_config_type_0(self):  # pragma: no cover # WIP
        """Method decodes floor configuration type 0"""
        raise NotImplementedError()

    def _process_floors(self):
        """Method processes floors for current logical bitstream"""
        current_stream = self.logical_streams[-1]

        vorbis_floor_count = self._read_bits_for_int(6) + 1
        current_stream.vorbis_floor_types = []
        current_stream.vorbis_floor_configurations = []
        for i in range(vorbis_floor_count):
            current_stream.vorbis_floor_types.append(
                self._read_bits_for_int(16))
            if current_stream.vorbis_floor_types[i] == 1:
                current_stream.vorbis_floor_configurations.append(
                    self._decode_floor_config_type_1())
            elif current_stream.vorbis_floor_types[i] == 0:
                current_stream.vorbis_floor_configurations.append(
                    self._decode_floor_config_type_0())
            else:
                raise CorruptedFileDataError(
                    'Nonsupported floor type: '
                    + str(current_stream.vorbis_floor_types[i]))

    # floor decoding # end
    # residue decoding # start

    @dataclass
    class ResidueData:  # pragma: no cover
        """Class for storing residue data"""
        residue_begin: int
        residue_end: int
        residue_partition_size: int
        residue_classifications: int
        residue_classbook: int
        residue_cascade: list
        residue_books: list

    def _decode_residue_config(self):  # A bit of unclear code
        """Method decodes residue configuration"""
        current_stream = self.logical_streams[-1]

        residue_begin = self._read_bits_for_int(24)
        residue_end = self._read_bits_for_int(24)
        residue_partition_size = self._read_bits_for_int(24) + 1
        residue_classifications = self._read_bits_for_int(6) + 1
        residue_classbook = self._read_bits_for_int(8)
        if (residue_classbook
                > len(current_stream.vorbis_codebook_configurations)):
            raise CorruptedFileDataError(
                'Received incorrect [residue_classbook]'
                'while residue config decoding: '
                + str(residue_classbook))

        # If [residue_classifications]ˆ[residue_classbook].dimensions exceeds
        # [residue_classbook].entries, the bitstream should be regarded to be
        # undecodable. ???

        residue_cascade = []
        for i in range(residue_classifications):
            high_bits = 0
            low_bits = self._read_bits_for_int(3)
            bitflag = self._read_bit()
            if bitflag:
                high_bits = self._read_bits_for_int(5)
            residue_cascade.append(high_bits * 8 + low_bits)

        residue_books = []
        for i in range(residue_classifications):
            residue_books.append([])
            for j in range(8):
                if (residue_cascade[i] & (1 << j)) != 0:
                    residue_books[i].append(self._read_bits_for_int(8))
                    if (residue_books[i][j]
                            > len(current_stream.
                                  vorbis_codebook_configurations)):
                        raise CorruptedFileDataError(
                            'Received incorrect [residue_books] item '
                            'while residue config decoding'
                            '(number greater than codebook number): '
                            + str(residue_books[i][j]))
                    if (current_stream.
                            vorbis_codebook_configurations[
                                residue_books[i][j]].codebook_lookup_type
                            == 0):
                        raise CorruptedFileDataError(
                            'Received incorrect [residue_books] item '
                            'while residue config decoding'
                            '(lookup_type is zero): '
                            + str(residue_books[i][j]))
                else:
                    residue_books[i].append(-1)

        return self.ResidueData(
            residue_begin,
            residue_end,
            residue_partition_size,
            residue_classifications,
            residue_classbook,
            residue_cascade,
            residue_books)

    def _process_residues(self):
        """Method processes residues for current logical bitstream"""
        current_stream = self.logical_streams[-1]

        vorbis_residue_count = self._read_bits_for_int(6) + 1
        current_stream.vorbis_residue_types = []
        current_stream.vorbis_residue_configurations = []
        for i in range(vorbis_residue_count):
            current_stream.vorbis_residue_types.append(
                self._read_bits_for_int(16))
            if 0 <= current_stream.vorbis_residue_types[i] < 3:
                current_stream.vorbis_residue_configurations.append(
                    self._decode_residue_config())
            else:
                raise CorruptedFileDataError(
                    'Nonsupported residue type: '
                    + str(current_stream.vorbis_residue_types[i]))

    # residue decoding # end
    # mapping decoding # start

    @dataclass
    class MappingData:  # pragma: no cover
        """Class for storing mapping data"""
        vorbis_mapping_submaps: int
        vorbis_mapping_coupling_steps: int
        vorbis_mapping_magnitude: list
        vorbis_mapping_angle: list
        vorbis_mapping_mux: list
        vorbis_mapping_submap_floor: list
        vorbis_mapping_submap_residue: list

    def _process_mappings(self):
        """Method processes mappings for current logical bitstream"""
        current_stream = self.logical_streams[-1]

        vorbis_mapping_count = self._read_bits_for_int(6) + 1
        current_stream.vorbis_mapping_configurations = []
        for i in range(vorbis_mapping_count):
            mapping_type = self._read_bits_for_int(16)
            if mapping_type != 0:
                raise CorruptedFileDataError(
                    'Nonzero mapping type')

            vorbis_mapping_submaps = 1
            if self._read_bit():
                vorbis_mapping_submaps = self._read_bits_for_int(4) + 1

            vorbis_mapping_coupling_steps = 0
            vorbis_mapping_magnitude = []
            vorbis_mapping_angle = []
            if self._read_bit():
                vorbis_mapping_coupling_steps = self._read_bits_for_int(8) + 1
                for j in range(vorbis_mapping_coupling_steps):
                    vorbis_mapping_magnitude.append(
                        self._read_bits_for_int(
                            ilog(current_stream.audio_channels - 1)))
                    vorbis_mapping_angle.append(
                        self._read_bits_for_int(
                            ilog(current_stream.audio_channels - 1)))
                    if (vorbis_mapping_angle[j] == vorbis_mapping_magnitude[j]
                            or vorbis_mapping_magnitude[j]
                            > current_stream.audio_channels - 1
                            or vorbis_mapping_angle[j]
                            > current_stream.audio_channels - 1):
                        raise CorruptedFileDataError(
                            'Received incorrect [vorbis_mapping_angle] '
                            'or [vorbis_mapping_magnitude] item(s)')

            reserved_field = self._read_bits_for_int(2)
            if reserved_field != 0:
                raise CorruptedFileDataError(
                    '[reserved_field] is nonzero')

            vorbis_mapping_mux = []
            if vorbis_mapping_submaps > 1:
                for j in range(current_stream.audio_channels):
                    vorbis_mapping_mux.append(self._read_bits_for_int(4))
                    if vorbis_mapping_mux > vorbis_mapping_submaps - 1:
                        raise CorruptedFileDataError(
                            'Received incorrect [vorbis_mapping_mux] item')

            vorbis_mapping_submap_floor = []
            vorbis_mapping_submap_residue = []
            for j in range(vorbis_mapping_submaps):
                self._read_bits_for_int(8)  # placeholder
                vorbis_mapping_submap_floor.append(self._read_bits_for_int(8))
                if (vorbis_mapping_submap_floor[j]
                        > max(current_stream.vorbis_floor_types)):
                    raise CorruptedFileDataError(
                        'Received incorrect [vorbis_mapping_submap_floor] '
                        'item: ' + str(vorbis_mapping_submap_floor[j]))

                vorbis_mapping_submap_residue.append(
                    self._read_bits_for_int(8))
                if (vorbis_mapping_submap_residue[j]
                        > max(current_stream.vorbis_residue_types)):
                    raise CorruptedFileDataError(
                        'Received incorrect [vorbis_mapping_submap_residue] '
                        'item: ' + str(vorbis_mapping_submap_residue[j]))

            current_stream.vorbis_mapping_configurations.append(
                self.MappingData(
                    vorbis_mapping_submaps,
                    vorbis_mapping_coupling_steps,
                    vorbis_mapping_magnitude,
                    vorbis_mapping_angle,
                    vorbis_mapping_mux,
                    vorbis_mapping_submap_floor,
                    vorbis_mapping_submap_residue))

    # mapping decoding # end

    # TODO
    def _process_setup_header(self):
        """Method process setup header storing info in appropriate \
[logical_stream] object"""
        self._check_header_sync_pattern()
        current_stream = self.logical_streams[-1]

        vorbis_codebook_count = self._read_bits_for_int(8) + 1
        current_stream.vorbis_codebook_configurations = []
        for i in range(vorbis_codebook_count):
            current_stream.vorbis_codebook_configurations.append(
                self._codebook_decoder.read_codebook())

        vorbis_time_count = self._read_bits_for_int(6) + 1
        for i in range(vorbis_time_count):
            placeholder = self._read_bits_for_int(16)
            if placeholder != 0:
                raise CorruptedFileDataError(
                    '[vorbis_time_count] placeholders '
                    'are contain nonzero value. Number: '
                    + str(i))

        self._process_floors()

        self._process_residues()

        self._process_mappings()

        vorbis_mode_count = self._read_bits_for_int(6) + 1
        current_stream.vorbis_mode_configurations = []
        for i in range(vorbis_mode_count):
            vorbis_mode_blockflag = self._read_bit()
            vorbis_mode_windowtype = self._read_bits_for_int(16)
            vorbis_mode_transformtype = self._read_bits_for_int(16)
            vorbis_mode_mapping = self._read_bits_for_int(8)
            if (vorbis_mode_windowtype != 0
                    or vorbis_mode_transformtype != 0):
                raise CorruptedFileDataError(
                    'Received incorrect [vorbis_mode_windowtype] or '
                    '[vorbis_mode_transformtype] or [vorbis_mode_mapping]: '
                    + str(vorbis_mode_windowtype) + ' '
                    + str(vorbis_mode_transformtype))
            if (vorbis_mode_mapping
                    > len(current_stream.vorbis_mapping_configurations)):
                raise CorruptedFileDataError(
                    'Received incorrect [vorbis_mode_mapping]: '
                    + str(vorbis_mode_mapping))

            current_stream.vorbis_mode_configurations.append(
                (vorbis_mode_blockflag, vorbis_mode_mapping))

        if not self._read_bit():
            raise CorruptedFileDataError(
                'Framing bit lost while setup header decoding')

    def process_headers(self):
        """Method process headers in whole file creating [logical_stream] \
objects"""
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
                self.logical_streams[-1].comment_header_decoding_failed = \
                    False
                try:
                    self._process_comment_header()
                except EndOfPacketException:
                    self.logical_streams[-1].comment_header_decoding_failed =\
                        True

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
