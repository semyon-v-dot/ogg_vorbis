from typing import Optional, Callable, List, Tuple

from .ogg import PacketsReader, CorruptedFileDataError, FileDataException
from .helper_funcs import float32_unpack, ilog, bit_reverse, lookup1_values


class EndOfPacketException(FileDataException):
    """Raised when end-of-packet condition triggered

    From docs:
    "Attempting to read past the end of an encoded packet results in an
    ’end-of-packet’ condition. End-of-packet is not to be considered an error;
    it is merely a state indicating that there is insufficient remaining data
    to fulfill the desired read size."
    """
    pass


class AbstractDecoder:
    """Methods shortcuts for _DataReader methods

    These methods are used too often in process of decoding data. So shortcuts
    are presented"""
    _read_bit: Callable[[], int]
    _read_bytes: Callable[[int], bytes]
    _read_bits_for_int: Callable[[int, bool], int]

    _get_current_global_position: Callable[[], Tuple[int, int]]

    def __init__(self, data_reader: 'DataReader'):
        self._read_bit = data_reader.read_bit
        self._read_bytes = data_reader.read_bytes
        self._read_bits_for_int = data_reader.read_bits_for_int

        self._get_current_global_position = (
            data_reader.get_current_global_position)


class SetupHeaderDecoder(AbstractDecoder):
    """Class represents decoder of vorbis codebooks"""
    class CodebookData:
        """Output data from codebook decoding"""
        codebook_codewords: List[str]
        VQ_lookup_table: List[List[float]]
        codebook_lookup_type: int
        codebook_dimensions: int
        codebook_entries: int

    class FloorData:
        floor1_partition_class_list: List[int]
        floor1_class_dimensions: List[int]
        floor1_class_subclasses: List[int]
        floor1_class_masterbooks: List[Optional[int]]
        floor1_subclass_books: List[List[int]]
        floor1_multiplier: int
        floor1_x_list: List[int]
        floor1_values: int

    class ResidueData:
        residue_begin: int
        residue_end: int
        residue_partition_size: int
        residue_classifications: int
        residue_classbook: int
        residue_cascade: List[int]
        residue_books: List[List[Optional[int]]]

    class MappingData:
        vorbis_mapping_submaps: int
        vorbis_mapping_coupling_steps: int
        vorbis_mapping_magnitude: List[int]
        vorbis_mapping_angle: List[int]
        vorbis_mapping_mux: List[int]
        vorbis_mapping_submap_floor: List[int]
        vorbis_mapping_submap_residue: List[int]

    # All class' vars below related to codebooks decoding ONLY

    last_read_codebook_position: Tuple[int, int]

    # Amount of scalars in every VQ table vector
    _codebook_dimensions: int

    # Amount of codewords
    _codebook_entries: int

    # Flags for codewords lengths unpacking
    _ordered: bool
    _sparse: bool

    # Data for Huffman tree decoding
    _codebook_codewords_lengths: List[Optional[int]]

    # Acquired from Huffman tree decoding
    # List of decoded codewords
    _codebook_codewords: List[str]

    # Data below for VQ lookup table unpacking
    _codebook_lookup_type: int
    _codebook_minimum_value: float
    _codebook_delta_value: float
    _codebook_value_bits: int
    _codebook_sequence_p: bool
    _codebook_lookup_values: int
    _codebook_multiplicands: List[int]

    # Acquired from vq lookup table unpacking
    _VQ_lookup_table: List[List[float]]

    def __init__(self, data_reader: 'DataReader'):
        super().__init__(data_reader)

    def read_codebook(self) -> CodebookData:
        """Method reads full codebook from packet data"""
        self.last_read_codebook_position = self._get_current_global_position()

        result_data: SetupHeaderDecoder.CodebookData = self.CodebookData()

        self._check_codebook_sync_pattern()

        self._codebook_dimensions = self._read_bits_for_int(16)
        result_data.codebook_dimensions = self._codebook_dimensions

        self._codebook_entries = self._read_bits_for_int(24)
        result_data.codebook_entries = self._codebook_entries

        if self._codebook_entries == 1:
            raise CorruptedFileDataError('Single codebook entry was given')

        self._ordered = bool(self._read_bit())
        if not self._ordered:
            self._sparse = bool(self._read_bit())

        self._codebook_codewords_lengths = self._read_codeword_lengths()

        self._codebook_codewords = self._huffman_decode()
        result_data.codebook_codewords = list(self._codebook_codewords)

        self._codebook_lookup_type = self._read_bits_for_int(4)
        result_data.codebook_lookup_type = self._codebook_lookup_type

        if (self._codebook_lookup_type < 0
                or self._codebook_lookup_type > 2):
            raise CorruptedFileDataError(
                'Not supported lookup type: '
                + str(self._codebook_lookup_type))

        if self._codebook_lookup_type != 0:
            self._codebook_minimum_value = float32_unpack(
                self._read_bits_for_int(32))

            self._codebook_delta_value = float32_unpack(
                self._read_bits_for_int(32))

            self._codebook_value_bits = self._read_bits_for_int(4) + 1

            self._codebook_sequence_p = bool(self._read_bit())

            if self._codebook_sequence_p:
                raise NotImplementedError("[_codebook_sequence_p] is True")

            if self._codebook_lookup_type == 1:
                self._codebook_lookup_values = lookup1_values(
                    self._codebook_entries, self._codebook_dimensions)
            else:
                self._codebook_lookup_values = (
                    self._codebook_entries * self._codebook_dimensions)

            self._codebook_multiplicands = []
            for i in range(self._codebook_lookup_values):
                self._codebook_multiplicands.append(
                    self._read_bits_for_int(self._codebook_value_bits))

            self._VQ_lookup_table = self._vq_lookup_table_unpack()
            result_data.VQ_lookup_table = list(self._VQ_lookup_table)

            return result_data

        result_data.VQ_lookup_table = []

        return result_data

    def _check_codebook_sync_pattern(self):
        """Checks if there is a codebook sync pattern in packet data"""
        if self._read_bytes(3) != b'BCV':
            raise CorruptedFileDataError('Codebook sync pattern is absent')

    def _read_codeword_lengths(self) -> List[Optional[int]]:
        """Method reads codewords lengths from packet data"""
        result_codeword_lengths: List[Optional[int]] = []

        if not self._ordered:
            for i in range(self._codebook_entries):
                if self._sparse:
                    flag: bool = bool(self._read_bit())

                    if flag:
                        result_codeword_lengths.append(
                            self._read_bits_for_int(5) + 1)
                    else:
                        result_codeword_lengths.append(None)
                else:
                    result_codeword_lengths.append(
                        self._read_bits_for_int(5) + 1)
        else:
            current_entry: int = 0
            current_length: int = self._read_bits_for_int(5) + 1

            while current_entry < self._codebook_entries:
                number = self._read_bits_for_int(
                    ilog(self._codebook_entries - current_entry))

                for i in range(current_entry, current_entry + number):
                    result_codeword_lengths.append(current_length)

                current_entry = number + current_entry
                current_length += 1

                if current_entry > self._codebook_entries:
                    raise CorruptedFileDataError(
                        "Incorrect codebook lengths coding")

        # Error due to 'bit_reverse' helper function
        if any(item is not None and item > 32
               for item in result_codeword_lengths):
            raise CorruptedFileDataError("Entry length greater than 32")

        return result_codeword_lengths

    def _huffman_decode(self) -> List[str]:
        """Decodes Huffman tree with int codewords representation method"""
        result_codewords: List[str] = []

        for start_entry in range(self._codebook_entries):
            if self._codebook_codewords_lengths[start_entry] is not None:
                break
            result_codewords.append('')
        else:
            return result_codewords

        result_codewords.append(
            ''.zfill(self._codebook_codewords_lengths[start_entry]))

        available: List[int] = [0] * 32
        for i in range(1,
                       self._codebook_codewords_lengths[start_entry] + 1):
            available[i] = 1 << (32 - i)

        for i in range(start_entry + 1, self._codebook_entries):
            max_available_branch = self._codebook_codewords_lengths[i]

            if max_available_branch is None:
                result_codewords.append('')
                continue

            while (max_available_branch > 0
                   and available[max_available_branch] == 0):
                max_available_branch -= 1

            assert 0 < max_available_branch < 32

            result = available[max_available_branch]
            available[max_available_branch] = 0

            codeword: str = bin(bit_reverse(result))[2:]
            codeword = (
                ''.zfill(
                    self._codebook_codewords_lengths[i] - len(
                        codeword))
                + codeword)
            result_codewords.append(codeword[::-1])

            if max_available_branch != self._codebook_codewords_lengths[i]:
                for new_branch in range(
                        self._codebook_codewords_lengths[i],
                        max_available_branch,
                        -1):
                    assert available[new_branch] == 0
                    available[new_branch] = result + (
                        1 << (32 - new_branch))

        return result_codewords

    def _vq_lookup_table_unpack(self) -> List[List[float]]:
        """Decodes VQ lookup table from some values in packet data"""
        result_vq_table: List[List[float]] = []

        if self._codebook_lookup_type == 1:
            for lookup_offset in range(self._codebook_entries):
                last: float = 0
                index_divisor: int = 1
                value_vector: List[float] = []

                for i in range(self._codebook_dimensions):
                    multiplicand_offset = (
                        (lookup_offset // index_divisor)
                        % self._codebook_lookup_values)
                    value_vector.append(
                        self._codebook_multiplicands[multiplicand_offset]
                        * self._codebook_delta_value
                        + self._codebook_minimum_value
                        + last)

                    if self._codebook_sequence_p:
                        last = value_vector[i]

                    index_divisor *= self._codebook_lookup_values

                result_vq_table.append(value_vector)

        elif self._codebook_lookup_type == 2:
            raise NotImplementedError(
                'VQ lookup table unpacking with [_codebook_lookup_type] = 2')
            # for lookup_offset in range(self._codebook_entries):
            #     last: float = 0
            #     multiplicand_offset: int = (
            #             lookup_offset * self._codebook_dimensions)
            #     value_vector: List[float] = []
            #
            #     for i in range(self._codebook_dimensions):
            #         value_vector.append(
            #             self._codebook_multiplicands[multiplicand_offset]
            #             * self._codebook_delta_value
            #             + self._codebook_minimum_value
            #             + last)
            #
            #         if self._codebook_sequence_p:
            #             last = value_vector[i]
            #
            #         multiplicand_offset += 1
            #
            #     result_vq_table.append(value_vector)

        else:
            raise CorruptedFileDataError(
                'Got illegal codebook lookup type: '
                f'{self._codebook_lookup_type}')

        return result_vq_table

    def _huffman_decode_bfc(self) -> List[str]:
        """Decodes Huffman tree with brute force method

        Extremely slow code! Use for tests ONLY!"""
        return_values: List[str] = []
        for i in range(0, self._codebook_entries):
            if self._codebook_codewords_lengths[i] is None:
                return_values.append('')
                continue

            bfc_value: str = (
                ''.join(["1" for i in range(
                    self._codebook_codewords_lengths[i])]))
            for value in return_values:
                if len(value) == len(bfc_value) and \
                        int(value, 2) < int(bfc_value, 2):
                    bfc_value = value
            if '0' not in bfc_value:
                bfc_value = ''.zfill(self._codebook_codewords_lengths[i])

            while '0' in bfc_value:
                for value in return_values:
                    prefix_length = min(len(value), len(bfc_value))
                    if (prefix_length != 0
                        and value[:prefix_length]
                            == bfc_value[:prefix_length]):
                        break
                else:
                    break

                bfc_value = (
                    bin(int(bfc_value, 2) + 1)[2:]
                    .zfill(self._codebook_codewords_lengths[i]))

            return_values.append(bfc_value)

        self._huffman_bfc_fullness_check(return_values)

        return return_values

    @staticmethod
    def _huffman_bfc_fullness_check(codewords: List[str]):
        """Method checks if decoded Huffman tree is full

        Slow code!"""
        for codeword_1 in codewords:
            if len(codeword_1) == 0:
                continue

            paired_node_is_present = False
            for codeword_2 in codewords:
                if len(codeword_2) == 0 or codeword_1 == codeword_2:
                    continue

                min_len = min(len(codeword_1), len(codeword_2))
                if codeword_1[:min_len - 1] == codeword_2[:min_len - 1]:
                    paired_node_is_present = True
                    break
            if not paired_node_is_present:
                raise CorruptedFileDataError(
                    'Huffman tree is underspecified')

    def read_floors(
            self, codebooks_amount: int) -> Tuple[List[int], List[FloorData]]:
        """Returns tuple of floors' types AND related floors' data

        Input data from current logical stream"""
        vorbis_floor_types: List[int] = []
        vorbis_floor_configurations: List['SetupHeaderDecoder.FloorData'] = []

        for i in range(self._read_bits_for_int(6) + 1):
            vorbis_floor_types.append(self._read_bits_for_int(16))

            if vorbis_floor_types[i] == 1:
                vorbis_floor_configurations.append(
                    self._decode_floor_config_type_1(codebooks_amount))

            elif vorbis_floor_types[i] == 0:
                vorbis_floor_configurations.append(
                    self._decode_floor_config_type_0())

            else:
                raise CorruptedFileDataError(
                    f'Not supported floor type: {vorbis_floor_types[i]}')

        return vorbis_floor_types, vorbis_floor_configurations

    # WouldBeBetter: Floor config type 0 decoding. Check docstring for details
    def _decode_floor_config_type_0(self) -> FloorData:
        """Method decodes floor configuration type 0

        From Vorbis I docs:
        "Floor 0 is not to be considered deprecated, but it is of limited
        modern use. No known Vorbis encoder past Xiph.Org’s own beta 4 makes
        use of floor 0."
        """
        raise NotImplementedError('Floor 0 decoding')

    def _decode_floor_config_type_1(self, codebooks_amount: int) -> FloorData:
        """Method decodes floor configuration type 1"""
        result_data: 'SetupHeaderDecoder.FloorData' = self.FloorData()

        floor1_partitions = self._read_bits_for_int(5)
        result_data.floor1_partition_class_list = []

        for i in range(floor1_partitions):
            result_data.floor1_partition_class_list.append(
                self._read_bits_for_int(4))

        maximum_class = max(result_data.floor1_partition_class_list)

        result_data.floor1_class_dimensions = []
        result_data.floor1_class_subclasses = []
        result_data.floor1_class_masterbooks = []
        result_data.floor1_subclass_books = []

        for i in range(maximum_class + 1):
            result_data.floor1_class_dimensions.append(
                self._read_bits_for_int(3) + 1)

            result_data.floor1_class_subclasses.append(
                self._read_bits_for_int(2))

            if result_data.floor1_class_subclasses[i] != 0:
                result_data.floor1_class_masterbooks.append(
                    self._read_bits_for_int(8))
            else:
                result_data.floor1_class_masterbooks.append(None)

            result_data.floor1_subclass_books.append([])

            for j in range(1 << result_data.floor1_class_subclasses[i]):
                result_data.floor1_subclass_books[i].append(
                    self._read_bits_for_int(8) - 1)

        result_data.floor1_multiplier = self._read_bits_for_int(2) + 1
        range_bits = self._read_bits_for_int(4)
        result_data.floor1_x_list = [0, 1 << range_bits]
        result_data.floor1_values = 2

        for i in range(floor1_partitions):
            current_class_number = result_data.floor1_partition_class_list[i]

            for j in range(
                    result_data.floor1_class_dimensions[current_class_number]):
                result_data.floor1_x_list.append(
                    self._read_bits_for_int(range_bits))
                result_data.floor1_values += 1

        if any(item is not None and item > codebooks_amount
               for item in result_data.floor1_class_masterbooks):
            raise CorruptedFileDataError(
                'Received [floor1_class_masterbooks] item greater than '
                f'{codebooks_amount}: '
                + str(result_data.floor1_class_masterbooks))

        if any(any(scalar > codebooks_amount for scalar in vector)
                for vector in result_data.floor1_subclass_books):
            raise CorruptedFileDataError(
                'Received [floor1_subclass_books] item greater than '
                f'{codebooks_amount}: '
                + str(result_data.floor1_subclass_books))

        if len(result_data.floor1_x_list) > 65:
            raise CorruptedFileDataError(
                '[floor1_X_list] have more than 65 elements')

        if (len(result_data.floor1_x_list)
                != len(set(result_data.floor1_x_list))):
            raise CorruptedFileDataError(
                '[floor1_X_list] have not unique elements: '
                + str(result_data.floor1_x_list))

        return result_data

    def read_residues(
            self,
            codebooks_configs: List['SetupHeaderDecoder.CodebookData']
            ) -> Tuple[List[int], List[ResidueData]]:
        """Returns tuple of residues types AND related residues' data

        Input data from current logical stream"""
        vorbis_residue_types: List[int] = []
        vorbis_residue_configurations: (
            List['SetupHeaderDecoder.ResidueData']) = []

        for i in range(self._read_bits_for_int(6) + 1):
            vorbis_residue_types.append(self._read_bits_for_int(16))

            if 0 <= vorbis_residue_types[i] < 3:
                vorbis_residue_configurations.append(
                    self._decode_residue_config(codebooks_configs))
            else:
                raise CorruptedFileDataError(
                    'Not supported residue type: '
                    + str(vorbis_residue_types[i]))

        return vorbis_residue_types, vorbis_residue_configurations

    def _decode_residue_config(
            self,
            codebooks_configs: List['SetupHeaderDecoder.CodebookData']
            ) -> ResidueData:
        """Method decodes residue configuration"""
        result_data: 'SetupHeaderDecoder.ResidueData' = self.ResidueData()

        result_data.residue_begin = self._read_bits_for_int(24)
        result_data.residue_end = self._read_bits_for_int(24)
        result_data.residue_partition_size = self._read_bits_for_int(24) + 1
        result_data.residue_classifications = self._read_bits_for_int(6) + 1
        result_data.residue_classbook = self._read_bits_for_int(8)

        if result_data.residue_classbook > len(codebooks_configs):
            raise CorruptedFileDataError(
                'Received incorrect [residue_classbook]'
                + str(result_data.residue_classbook))

        # Not obvious way to code things, so errors can occur with
        # [coded_codebook]

        coded_codebook: SetupHeaderDecoder.CodebookData = (
            codebooks_configs[
                result_data.residue_classifications
                ^ result_data.residue_classbook])

        residue_classbook_codebook: SetupHeaderDecoder.CodebookData = (
            codebooks_configs[result_data.residue_classbook])

        if (coded_codebook.codebook_dimensions >
                residue_classbook_codebook.codebook_entries):
            raise CorruptedFileDataError(
                '[residue_classbook].dimensions exceeds '
                '[residue_classbook].entries: '
                + str(coded_codebook.codebook_dimensions) + ' > '
                + str(residue_classbook_codebook.codebook_entries))

        result_data.residue_cascade = []

        for i in range(result_data.residue_classifications):
            high_bits: int = 0
            low_bits: int = self._read_bits_for_int(3)
            bitflag: bool = bool(self._read_bit())

            if bitflag:
                high_bits = self._read_bits_for_int(5)

            result_data.residue_cascade.append(high_bits * 8 + low_bits)

        result_data.residue_books = []

        for i in range(result_data.residue_classifications):
            result_data.residue_books.append([])

            for j in range(8):
                if (result_data.residue_cascade[i] & (1 << j)) != 0:
                    result_data.residue_books[i].append(
                        self._read_bits_for_int(8))

                    # Some checks next

                    if (result_data.residue_books[i][j] >
                            len(codebooks_configs)):
                        raise CorruptedFileDataError(
                            'Last received into [residue_books] item is '
                            'incorrect, greater than codebook number '
                            f'[{len(codebooks_configs)}]: '
                            + str(result_data.residue_books))

                    if (codebooks_configs[result_data.residue_books[i][j]]
                            .codebook_lookup_type == 0):
                        raise CorruptedFileDataError(
                            'Received incorrect [residue_books] item, '
                            'lookup type of '
                            f'[{result_data.residue_books[i][j]}] '
                            'codebook is zero')

                else:
                    result_data.residue_books[i].append(None)

        return result_data

    def read_mappings(
            self,
            audio_channels: int,
            amount_of_floors: int,
            amount_of_residues: int) -> List[MappingData]:
        """Method processes mappings for current logical bitstream

        Input data from current logical stream"""
        vorbis_mapping_configurations: (
            List['SetupHeaderDecoder.MappingData']) = []

        for i in range(self._read_bits_for_int(6) + 1):
            vorbis_mapping_configurations.append(
                self._decode_mapping_config(
                    audio_channels, amount_of_floors, amount_of_residues))

        return vorbis_mapping_configurations

    def _decode_mapping_config(
            self,
            audio_channels: int,
            amount_of_floors: int,
            amount_of_residues: int) -> MappingData:
        result_data: 'SetupHeaderDecoder.MappingData' = self.MappingData()

        mapping_type = self._read_bits_for_int(16)

        if mapping_type != 0:
            raise CorruptedFileDataError('Nonzero mapping type')

        result_data.vorbis_mapping_submaps = 1

        if bool(self._read_bit()):
            result_data.vorbis_mapping_submaps = (
                self._read_bits_for_int(4) + 1)
        else:
            result_data.vorbis_mapping_submaps = 1

        result_data.vorbis_mapping_magnitude = []
        result_data.vorbis_mapping_angle = []

        if bool(self._read_bit()):
            result_data.vorbis_mapping_coupling_steps = (
                self._read_bits_for_int(8) + 1)

            for j in range(result_data.vorbis_mapping_coupling_steps):
                result_data.vorbis_mapping_magnitude.append(
                    self._read_bits_for_int(
                        ilog(audio_channels - 1)))
                result_data.vorbis_mapping_angle.append(
                    self._read_bits_for_int(
                        ilog(audio_channels - 1)))

                if (result_data.vorbis_mapping_angle[j]
                        == result_data.vorbis_mapping_magnitude[j]
                        or result_data.vorbis_mapping_magnitude[j]
                        > audio_channels - 1
                        or result_data.vorbis_mapping_angle[j]
                        > audio_channels - 1):
                    raise CorruptedFileDataError(
                        'Received incorrect [vorbis_mapping_angle] '
                        'or [vorbis_mapping_magnitude] item(s)')
        else:
            result_data.vorbis_mapping_coupling_steps = 0

        if self._read_bits_for_int(2) != 0:  # Reserved field
            raise CorruptedFileDataError('[reserved_field] is nonzero')

        result_data.vorbis_mapping_mux = []

        if result_data.vorbis_mapping_submaps > 1:
            for j in range(audio_channels):
                result_data.vorbis_mapping_mux.append(
                    self._read_bits_for_int(4))

                if (result_data.vorbis_mapping_mux[j]
                        > result_data.vorbis_mapping_submaps - 1):
                    raise CorruptedFileDataError(
                        'Received incorrect [vorbis_mapping_mux] item')

        result_data.vorbis_mapping_submap_floor = []
        result_data.vorbis_mapping_submap_residue = []

        for j in range(result_data.vorbis_mapping_submaps):
            self._read_bits_for_int(8)  # Placeholder

            result_data.vorbis_mapping_submap_floor.append(
                self._read_bits_for_int(8))

            if (result_data.vorbis_mapping_submap_floor[j]
                    >= amount_of_floors):
                raise CorruptedFileDataError(
                    'Received incorrect [vorbis_mapping_submap_floor] item: '
                    + str(result_data.vorbis_mapping_submap_floor[j]))

            result_data.vorbis_mapping_submap_residue.append(
                self._read_bits_for_int(8))

            if (result_data.vorbis_mapping_submap_residue[j]
                    >= amount_of_residues):
                raise CorruptedFileDataError(
                    'Received incorrect [vorbis_mapping_submap_residue] '
                    'item: '
                    + str(result_data.vorbis_mapping_submap_residue[j]))

        return result_data

    # TODO: '_read_modes_configs'
    def _read_modes_configs(
            self, mappings_amount: int) -> List[Tuple[bool, int]]:
        """

        Input data from current logical stream
        """
        modes_configs: List[Tuple[bool, int]] = []

        for i in range(self._read_bits_for_int(6) + 1):
            vorbis_mode_blockflag = bool(self._read_bit())
            vorbis_mode_windowtype = self._read_bits_for_int(16)
            vorbis_mode_transformtype = self._read_bits_for_int(16)
            vorbis_mode_mapping = self._read_bits_for_int(8)

            if vorbis_mode_windowtype != 0 or vorbis_mode_transformtype != 0:
                raise CorruptedFileDataError(
                    'Received incorrect [vorbis_mode_windowtype] or '
                    '[vorbis_mode_transformtype]: '
                    + str(vorbis_mode_windowtype)
                    + ' '
                    + str(vorbis_mode_transformtype))

            if vorbis_mode_mapping > mappings_amount:
                raise CorruptedFileDataError(
                    'Received incorrect [vorbis_mode_mapping]: '
                    + str(vorbis_mode_mapping))

            modes_configs.append((vorbis_mode_blockflag, vorbis_mode_mapping))

        return modes_configs


class DataReader:
    """Class for low-level data reading

    IMPORTANT: in bitstream bits have the next order:
    byte 1: 07 06 05 04 03 02 01 00
    byte 2: 15 14 13 12 11 10 09 08
    byte 3: 23 22 21 20 19 18 17 16
    etc.
    """
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
        self.set_packet_global_position(0)
        self._current_packet = b''
        self.byte_pointer = 0
        self.bit_pointer = 0

    def set_packet_global_position(self, new_position: int):
        """Method moves global position of [byte_pointer] in audio file"""
        self._packets_reader.move_byte_position(new_position)

    def get_packet_global_position(self) -> int:
        """Returns global position of current packet's beginning"""
        return (
            self._packets_reader.opened_file.tell()
            - len(self._current_packet))

    def get_current_global_position(self) -> Tuple[int, int]:
        """Returns current global position

        Returns in format: (<global byte>, <bit in this byte>)
        """
        return (
            self.get_packet_global_position() + self.byte_pointer,
            self.bit_pointer)

    def read_packet(self):
        """Method reads packet from [packets_reader]"""
        self._current_packet = self._packets_reader.read_packet()[0]
        self.byte_pointer = self.bit_pointer = 0

    def read_bytes(self, bytes_count: int) -> bytes:
        """Method reads and return several bytes from current packet

        IMPORTANT: method gives bytes in order: 1 2 3 4 5 6!"""
        assert bytes_count >= 0

        read_bytes = b''
        for i in range(bytes_count):
            read_bytes += bytes([int(self._read_bits(8), 2)])

        return read_bytes

    def read_bits_for_int(
            self, bits_count: int, signed: bool = False) -> int:
        """Reads bits from current packet for int value

        Reads [bits_count] bits from current packet and return unsigned int
        value"""
        assert bits_count >= 0

        number = self._read_bits(bits_count)

        if not signed or number[0] == '0':
            return int(number, 2)
        else:
            number = int(number, 2) - 1
            return -(number
                     ^ int(''.join(['1'] * bits_count), 2))

    def _read_bits(self, bits_count: int) -> str:
        """Method reads and return several bits from current packet data

        IMPORTANT: method gives bits in order: 6 5 4 3 2 1!"""
        assert bits_count >= 0

        read_bits = ''
        for i in range(bits_count):
            read_bits = str(self.read_bit()) + read_bits

        return read_bits

    def read_bit(self) -> int:
        """Method reads and return one bit from current packet data"""
        required_bit = 1
        try:
            if (self._current_packet[self.byte_pointer]
                    & (1 << self.bit_pointer) == 0):
                required_bit = 0
        except IndexError:
            raise EndOfPacketException('End of packet condition triggered')

        self.bit_pointer += 1
        if self.bit_pointer == 8:
            self.bit_pointer = 0
            self.byte_pointer += 1

        return required_bit
