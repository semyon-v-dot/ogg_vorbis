from .errors import *
from pathlib import Path


class PacketsReader:
    '''Class for reading packets'''
    def __init__(self, filename):
        filename = Path(filename)
        try:
            with open(filename, 'rb') as temp_file:
                self._file = temp_file.read()
        except FileNotFoundError:
            print("File name is incorrect: " + filename)
            exit(ERROR_INCORRECT_FILE_NAME)

        if self._file[:4] != b'OggS':
            print('File not an ogg container: ' + filename)
            exit(ERROR_FILE_FORMAT_NOT_OGG)

        self.byte_pointer = 0
        self._current_packet_data = b''

        self._packet_pages = []
        self._last_page = -1

# low-level data checks

    def _fresh_packet_on_page(self):
        '''Method returns True if fresh packet is on page'''
        if (self._file[self.byte_pointer + 5] & 1) == 0:
            return True
        else:
            return False

    ''' _last_page_of_logical_bitstream
    def _last_page_of_logical_bitstream(self):
        # Returns True if page is last in logical bitstream
        if (self._file[self.byte_pointer + 5] & 4) != 0:
            return True
        else:
            return False
    '''

    def _capture_pattern_not_on_place(self):
        '''Method returns True if page capture pattern not on place'''
        return self._file[self.byte_pointer:self.byte_pointer + 4] != b'OggS'

# moving byte_pointer in data

    def move_byte_pointer(self, new_position):
        '''Method moves [byte_pointer] to [new_position] and next to \
beginning of current packet'''
        if new_position < 0:
            raise ValueError('Received negative [new_position] while '
                             'changing [byte_pointer] position')

        self.byte_pointer = new_position
        self._current_packet_data = b''
        self._packet_pages = []

        if self._capture_pattern_not_on_place() or \
           not self._fresh_packet_on_page():
            self._move_to_page_beginning_above()
            while not self._fresh_packet_on_page():
                self.byte_pointer -= 1
                self._move_to_page_beginning_above()

        self._last_page = int.from_bytes(self._file[self.byte_pointer + 18:
                                         self.byte_pointer + 21],
                                         byteorder='little') - 1

    def _move_to_page_beginning_above(self):
        '''Method moves [byte_pointer] up until it reaches \
the beginning of a page'''
        while self._capture_pattern_not_on_place():
            if self.byte_pointer < 0:
                print("File data is corrupted. "
                      "Capture pattern is missing at the beginning")
                exit(ERROR_CORRUPTED_FILE_DATA_BEGINNING)
            self.byte_pointer -= 1

# page reading

    def _read_page_data(self):
        '''Method returns packet data of single page'''
        if self._capture_pattern_not_on_place():
            print('Missing ogg capture pattern in the beginning of '
                  'reading page data')
            exit(ERROR_MISSING_OGG_CAPTURE_PATTERN)

        # _fresh_packet_on_page
        #  first_page_of_logical_bitstream
        # _last_page_of_logical_bitstream
        #  absolute_granule_position
        #  stream_serial_number

        page_counter = int.from_bytes(self._file[self.byte_pointer + 18:
                                      self.byte_pointer + 21],
                                      byteorder='little')
        self._packet_pages += [page_counter]
        if page_counter != self._last_page + 1:
            print('Page(s) is(are) missing!\n'
                  'Previous last page: ' + str(self._last_page) + '\n'
                  'Current page: ' + str(page_counter) + '\n'
                  'Current [byte_pointer]: ' + str(self.byte_pointer))
            exit(ERROR_MISSING_PAGE)
        self._last_page += 1

        #  page_checksum

        page_segments_number = self._file[self.byte_pointer + 26]
        segment_table = \
            self._file[self.byte_pointer + 27:
                       self.byte_pointer + 27 + page_segments_number]
        segment_table_result = sum(segment_table)

        self.byte_pointer = self.byte_pointer + 27 + page_segments_number
        data = self._file[self.byte_pointer:
                          self.byte_pointer + segment_table_result]
        self.byte_pointer = self.byte_pointer + segment_table_result

        return data

    def _beginning_of_reading_actions(self):
        '''Method does actions in the beginning of the packet reading'''
        self._packet_pages = []
        self._current_packet_data = b''

    def read_packet(self):  # return (packet_data, packet_pages)
        '''Method returns packet data and packet pages'''
        if self.byte_pointer >= len(self._file) - 1:
            raise EOFError

        self._beginning_of_reading_actions()

        self._current_packet_data += self._read_page_data()
        while (not (self.byte_pointer >= len(self._file) - 1
                    or self._fresh_packet_on_page())):
            self._current_packet_data += self._read_page_data()

        return (self._current_packet_data, self._packet_pages)
