from .ogg import CorruptedFileDataError
from .helper_funcs import (
    shorter_attribute_creation, 
    float32_unpack, 
    lookup1_values, 
    ilog, 
    bit_reverse)
from dataclasses import dataclass


class CodebookDecoder:
    '''Class represents decoder of vorbis codebooks'''
    def __init__(self, data_reader):
        self._read_bit = data_reader.read_bit
        self._read_bits = data_reader.read_bits
        self._read_bits_for_int = data_reader.read_bits_for_int

        self._read_byte = data_reader.read_byte
        self._read_bytes = data_reader.read_bytes

    def _check_codebook_sync_pattern(self):
        '''Method checks if there is a codebook sync pattern in packet data'''
        pattern = self._read_bytes(3)

        if pattern != b'\x42\x43\x56':
            raise CorruptedFileDataError(
                'Codebook sync pattern is absent')

    def _read_codeword_lengths(self, 
            ordered, sparse, codebook_entries):  # assert codeword_length < 32
        '''Method reads codewords lengths from packet data'''
        returned_codeword_lengths = []
        if not ordered:
            for i in range(codebook_entries):
                if sparse:
                    flag = bool(self._read_bit())

                    if flag:
                        returned_codeword_lengths.append(
                            self._read_bits_for_int(5) + 1)
                    else:
                        returned_codeword_lengths.append(-1)
                else:
                    returned_codeword_lengths.append(
                        self._read_bits_for_int(5) + 1)
        else:
            current_entry = 0
            current_length = self._read_bits_for_int(5) + 1

            while current_entry < codebook_entries:
                number = self._read_bits_for_int(
                    ilog(codebook_entries - current_entry))

                for i in range(current_entry, current_entry + number):
                    returned_codeword_lengths.append(current_length)

                current_entry = number + current_entry
                current_length += 1

                if current_entry > codebook_entries:
                    raise CorruptedFileDataError(
                        "Incorrect codebook lengths coding")

        return returned_codeword_lengths

    def _Huffman_bfc_fullness_check(self, codewords):  # Slow code
        '''Method checks if decoded Huffman tree is full'''
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

    def _Huffman_decode_bfc(self,  # Extremely slow code!
                                 codebook_entries,
                                 codebook_codewords_lengths):
        '''Method decode Huffman tree from [codebook_entries] value and \
array [codebook_codewords_lengths] with brute force method'''
        return_values = []
        for i in range(0, codebook_entries):
            if codebook_codewords_lengths[i] == -1:
                return_values.append('')
                continue

            bfc_value = ''\
                .join(["1" for i in range(codebook_codewords_lengths[i])])
            for value in return_values:
                if len(value) == len(bfc_value) and \
                   int(value, 2) < int(bfc_value, 2):
                    bfc_value = value
            if '0' not in bfc_value:
                bfc_value = ''.zfill(codebook_codewords_lengths[i])

            while '0' in bfc_value:
                for value in return_values:
                    prefix_length = min(len(value), len(bfc_value))
                    if prefix_length != 0 and \
                       value[:prefix_length] == bfc_value[:prefix_length]:
                        break
                else:
                    break

                bfc_value = bin(int(bfc_value, 2) + 1)[2:]\
                    .zfill(codebook_codewords_lengths[i])

            return_values.append(bfc_value)

        self._Huffman_bfc_fullness_check(return_values)

        return return_values

    def _Huffman_decode_int_repres(self,
            codebook_entries,
            codewords_lengths):
        '''Method decode Huffman tree from [codebook_entries] value and \
array [codewords_lengths] with int codewords representation method'''
        assert codebook_entries == len(codewords_lengths)

        for start_entry in range(codebook_entries):
            if codewords_lengths[start_entry] != -1:
                break

            yield ''
        else:
            return

        yield ''.zfill(codewords_lengths[start_entry])

        available = [0 for i in range(32)]
        for i in range(1, codewords_lengths[start_entry] + 1):
            available[i] = 1 << (32 - i);

        for i in range(start_entry + 1, codebook_entries):  
            max_available_branch = codewords_lengths[i]

            if max_available_branch == -1:
                yield ''
                continue
            while (max_available_branch > 0 
                    and available[max_available_branch] == 0):
                max_available_branch -= 1
            assert 0 < max_available_branch < 32

            result = available[max_available_branch]
            available[max_available_branch] = 0

            codeword = bin(bit_reverse(result))[2:]
            codeword = (''.zfill(codewords_lengths[i] - len(codeword))
                        + codeword) 
            yield codeword

            if (max_available_branch != codewords_lengths[i]):
                for new_branch in range(
                        codewords_lengths[i], 
                        max_available_branch, 
                        -1):
                    assert available[new_branch] == 0
                    available[new_branch] = result + (1 << (32 - new_branch))

    def _VQ_lookup_table_unpack(self,  # Unclear code
                                codebook_multiplicands,
                                codebook_minimum_value, codebook_delta_value,
                                codebook_sequence_p,
                                codebook_lookup_type,
                                codebook_entries, codebook_dimensions,
                                codebook_lookup_values):
        '''Method decode VQ lookup table from some values from packet data'''
        if codebook_lookup_type == 1:
            for lookup_offset in range(codebook_entries):
                last = 0
                index_divisor = 1
                value_vector = []
                for i in range(codebook_dimensions):
                    multiplicand_offset = \
                        (lookup_offset // index_divisor) \
                        % codebook_lookup_values
                    value_vector.append(
                        codebook_multiplicands[multiplicand_offset]
                        * codebook_delta_value
                        + codebook_minimum_value
                        + last)
                    if codebook_sequence_p:
                        last = value_vector[i]
                    index_divisor *= codebook_lookup_values

                yield value_vector
        else:
            for lookup_offset in range(codebook_entries):
                last = 0
                multiplicand_offset = lookup_offset * codebook_dimensions
                value_vector = []
                for i in range(codebook_dimensions):
                    value_vector.append(
                        codebook_multiplicands[multiplicand_offset]
                        * codebook_delta_value
                        + codebook_minimum_value
                        + last)
                    if codebook_sequence_p:
                        last = value_vector[i]
                    multiplicand_offset += 1

                yield value_vector

    @dataclass
    class CodebookData:
        '''Class for storing codebook data'''
        codebook_codewords: tuple
        VQ_lookup_table: tuple
        codebook_lookup_type: int

    @shorter_attribute_creation
    def read_codebook(this, self):
        '''Method reads full codebook from packet data'''
        self._check_codebook_sync_pattern()

        this.codebook_dimensions = int.from_bytes(self._read_bytes(2),
                                                  byteorder='little')
        this.codebook_entries = int.from_bytes(self._read_bytes(3),
                                               byteorder='little')
        if this.codebook_entries == 1:
            raise CorruptedFileDataError('Single codebook entry given')
        this.ordered = bool(self._read_bit())
        if not this.ordered:
            this.sparse = bool(self._read_bit())
        this.codebook_codewords_lengths =\
            self._read_codeword_lengths(this.ordered,
                                        this.sparse,
                                        this.codebook_entries)
        this.codebook_codewords = tuple(
            self._Huffman_decode_int_repres(
                this.codebook_entries,
                this.codebook_codewords_lengths))

        this.codebook_lookup_type = self._read_bits_for_int(4)
        assert 0 <= this.codebook_lookup_type <= 2, (
            'Nonsupported lookup type: '
            + str(this.codebook_lookup_type))
        if this.codebook_lookup_type != 0:
            this.codebook_minimum_value =\
                float32_unpack(self._read_bits_for_int(32))
            this.codebook_delta_value =\
                float32_unpack(self._read_bits_for_int(32))
            this.codebook_value_bits = self._read_bits_for_int(4) + 1
            this.codebook_sequence_p = bool(self._read_bit())

            if this.codebook_lookup_type == 1:
                this.codebook_lookup_values = \
                    lookup1_values(
                        this.codebook_entries, this.codebook_dimensions)
            else:
                this.codebook_lookup_values = \
                    this.codebook_entries * this.codebook_dimensions

            this.codebook_multiplicands = []
            for i in range(this.codebook_lookup_values):
                this.codebook_multiplicands.append(
                    self._read_bits_for_int(
                        this.codebook_value_bits))

            this.VQ_lookup_table = tuple(
                self._VQ_lookup_table_unpack(
                    this.codebook_multiplicands,
                    this.codebook_minimum_value,
                    this.codebook_delta_value,
                    this.codebook_sequence_p,
                    this.codebook_lookup_type,
                    this.codebook_entries,
                    this.codebook_dimensions,
                    this.codebook_lookup_values))

            return self.CodebookData(
                this.codebook_codewords,
                this.VQ_lookup_table,
                this.codebook_lookup_type)

        return self.CodebookData(this.codebook_codewords, (), 0)
