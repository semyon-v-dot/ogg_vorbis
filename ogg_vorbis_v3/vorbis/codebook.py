from .helper_funcs import *
from .errors import *


class CodebookDecoder:
    '''Class represents decoder of vorbis codebooks'''
    def __init__(self, data_reader):
        self._read_bit = data_reader.read_bit
        self._read_byte = data_reader.read_byte
        self._read_bits_for_int = data_reader.read_bits_for_int

    def _check_codebook_sync_pattern(self):
        '''Method checks if there is a codebook sync pattern in packet data'''
        pattern = b''
        for i in range(3):
            pattern += self._read_byte()

        if pattern != b'\x42\x43\x56':
            print('Codebook sync pattern is absent')
            exit(ERROR_CODEBOOK_SYNC_PATTERN_IS_ABSENT)

    def _read_codeword_lengths(self, ordered, codebook_entries):
        '''Method reads codewords lengths from packet data'''
        returned_codeword_lengths = []
        if not ordered:
            sparse = bool(self._read_bit())

            for i in range(codebook_entries):
                if sparse:
                    flag = bool(self._read_bit())

                    if flag:
                        returned_codeword_lengths +=\
                            [self._read_bits_for_int(5) + 1]
                    else:
                        returned_codeword_lengths +=\
                            [-1]
                else:
                    returned_codeword_lengths +=\
                        [self._read_bits_for_int(5) + 1]
        else:
            current_entry = 0
            current_length = self._read_bits_for_int(5) + 1

            while current_entry < codebook_entries:
                number = self._read_bits_for_int(
                    ilog(codebook_entries - current_entry))

                for i in range(current_entry, current_entry + number):
                    returned_codeword_lengths += [current_length]

                current_entry = number + current_entry
                current_length += 1

                if current_entry > codebook_entries:
                    print("Incorrect codebook lengths coding")
                    exit(ERROR_CODEBOOK_LENGTHS_INCORRECT_CODING)

        return returned_codeword_lengths

    def _Huffman_tree_fullness_check(self, codewords):  # Slow code
        '''Method checks if decoded Huffman tree is full'''
        for i in range(len(codewords)):
            if len(codewords[i]) == 0:
                continue

            paired_node_is_present = False
            for j in range(len(codewords)):
                if len(codewords[j]) == 0:
                    continue

                min_len = min(len(codewords[i]), len(codewords[j]))
                if codewords[i][:min_len - 1] ==\
                   codewords[j][:min_len - 1] and\
                   codewords[i][min_len - 1] != codewords[j][min_len - 1]:
                    paired_node_is_present = True
                    break
            if not paired_node_is_present:
                print('Huffman tree is underspecified')
                exit(ERROR_HUFFMAN_TREE_IS_UNDERSPECIFIED)

    def _Huffman_tree_decode_bfc(self,  # Extremely slow code!
                                 codebook_entries,
                                 codebook_codeword_lengths):
        '''Method decode Huffman tree from [codebook_entries] value and \
array [codebook_codeword_lengths] with brute force method'''
        return_values = []
        for i in range(codebook_entries):
            if codebook_codeword_lengths[i] == -1:
                return_values += ['']
                continue

            bfs_value = ''\
                .join(["1" for i in range(codebook_codeword_lengths[i])])
            for value in return_values:
                if len(value) == len(bfs_value) and \
                   int(value, 2) < int(bfs_value, 2):
                    bfs_value = value
            if '0' not in bfs_value:
                bfs_value = ''.zfill(codebook_codeword_lengths[i])

            while '0' in bfs_value:
                for value in return_values:
                    prefix_length = min(len(value), len(bfs_value))
                    if prefix_length != 0 and \
                       value[:prefix_length] == bfs_value[:prefix_length]:
                        break
                else:
                    break

                bfs_value = bin(int(bfs_value, 2) + 1)[2:]\
                    .zfill(codebook_codeword_lengths[i])

            return_values += [bfs_value]

        self._Huffman_tree_fullness_check(return_values)

        return return_values

    def _Huffman_tree_decode(self,  # WIP
                             codebook_entries,
                             codebook_codeword_lengths,
                             ordered):
        '''Method decode Huffman tree from [codebook_entries] value and \
array [codebook_codeword_lengths] with accelerate table method, \
zlib/jpeg method or ...'''
        pass

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
                    value_vector +=\
                        [codebook_multiplicands[multiplicand_offset]
                         * codebook_delta_value
                         + codebook_minimum_value
                         + last]
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
                    value_vector +=\
                        [codebook_multiplicands[multiplicand_offset]
                         * codebook_delta_value
                         + codebook_minimum_value
                         + last]
                    if codebook_sequence_p:
                        last = value_vector[i]
                    multiplicand_offset += 1

                yield value_vector

    @shorter_attribute_creation
    def read_codebook(this, self):
        '''Method reads full codebook from packet data'''
        self._check_codebook_sync_pattern()

        this.codebook_dimensions = int.from_bytes(self._read_byte()
                                                  + self._read_byte(),
                                                  byteorder='little')
        this.codebook_entries = int.from_bytes(self._read_byte()
                                               + self._read_byte()
                                               + self._read_byte(),
                                               byteorder='little')
        if this.codebook_entries == 1:
            print('Single codebook entry')
            exit(ERROR_CODEBOOK_SINGLE_ENTRY)
        this.ordered = bool(self._read_bit())
        this.codebook_codeword_lengths =\
            self._read_codeword_lengths(this.ordered, this.codebook_entries)
        # this.codebook_codewords =\
        #     list(self._Huffman_tree_decode(this.codebook_entries,
        #                                    this.codebook_codeword_lengths))

        this.codebook_lookup_type = self._read_bits_for_int(4)
        if this.codebook_lookup_type > 2:
            raise ValueError('Nonsupported lookup type')
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
                this.codebook_multiplicands +=\
                    [self._read_bits_for_int(
                        this.codebook_value_bits)]

            this.VQ_lookup_table = list(
                self._VQ_lookup_table_unpack(
                    this.codebook_multiplicands,
                    this.codebook_minimum_value,
                    this.codebook_delta_value,
                    this.codebook_sequence_p,
                    this.codebook_lookup_type,
                    this.codebook_entries,
                    this.codebook_dimensions,
                    this.codebook_lookup_values))

            # return (this.codebook_codewords, this.VQ_lookup_table)
            return (this.codebook_codeword_lengths, this.VQ_lookup_table)
        # return (this.codebook_codewords, ())
        return (this.codebook_codeword_lengths, ())
