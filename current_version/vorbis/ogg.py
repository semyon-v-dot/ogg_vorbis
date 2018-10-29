class CorruptedFileDataError(Exception):
    '''Raised when file data is corrupted'''
    pass

class UnexpectedEndOfFileError(CorruptedFileDataError):
    '''Raised when end of file unexpectedly reached while data reading'''
    pass
    
class FileNotAnOggContainerError(Exception):
    '''Raised when input file not an ogg container'''
    pass 


class PacketsReader:
    '''Class for reading packets'''
    def __init__(self, filename):
        try:
            self.opened_file = open(filename, 'rb')
        except FileNotFoundError:
            raise FileNotFoundError("File not found: " + filename)
        except IsADirectoryError:
            raise IsADirectoryError('Directory name given: ' + filename)
        except PermissionError:
            raise PermissionError('No access to file: ' + filename)
        except OSError:
            raise OSError('File handling is impossible: ' + filename)

        if self._capture_pattern_not_on_current_position():
            raise FileNotAnOggContainerError(
                'File not an ogg container: ' + filename)

        self._current_packet_data = b''

        self._packet_pages = []
        self._last_page = -1

    def close_file(self):
        '''Method closes opened ogg-vorbis file'''
        self.opened_file.close()
        
# low-level data checks

    def _fresh_packet_on_current_page(self):
        '''Method returns True if fresh packet is on current page'''
        temp_ = self.opened_file.read(4)  # capture_pattern
        temp_ += self.opened_file.read(1)  # stream_structure_version
        if len(temp_) != 5:
            raise UnexpectedEndOfFileError()

        header_type_flag = self.opened_file.read(1)[0]
        self.opened_file.seek(-6, 1)

        return (header_type_flag & 1) == 0

    def _last_page_of_logical_bitstream_reached(self):
        '''Method returns True if fresh packet is on current page'''
        temp_ = self.opened_file.read(4)  # capture_pattern
        temp_ += self.opened_file.read(1)  # stream_structure_version
        if len(temp_) != 5:
            raise UnexpectedEndOfFileError()

        header_type_flag = self.opened_file.read(1)[0]
        self.opened_file.seek(-6, 1)

        return (header_type_flag & 4) == 4

    def _capture_pattern_not_on_current_position(self):
        '''Method returns True if page capture pattern not presented on current
 byte position'''
        capture_pattern = self.opened_file.read(4)

        self.opened_file.seek(-4, 1)
        return capture_pattern != b'OggS'

# moving byte pointer in data

    def move_byte_position(self, new_position):
        '''Method moves byte pointer to [new_position] and next to \
beginning of current packet'''
        assert new_position >= 0

        self.opened_file.seek(new_position)
        self._current_packet_data = b''
        self._packet_pages = []

        if (self._capture_pattern_not_on_current_position() 
                or not self._fresh_packet_on_current_page()):
            self._move_to_page_beginning_above()
            while not self._fresh_packet_on_current_page():
                if self.opened_file.tell() == 0:
                    raise CorruptedFileDataError(
                        '[header_type_flag]: 0x01 flag is set on '
                        'first page of the file')
                self.opened_file.seek(-1, 1)
                self._move_to_page_beginning_above()

        self.opened_file.read(18)
        self._last_page = int.from_bytes(
            self.opened_file.read(4), byteorder='little') - 1
        self.opened_file.seek(-22, 1)

    def _move_to_page_beginning_above(self):
        '''Method moves byte pointer up until it reaches \
the beginning of a page'''
        while self._capture_pattern_not_on_current_position():
            if self.opened_file.tell() == 0:
                raise CorruptedFileDataError(
                    "Capture pattern is missing at the beginning of the file")
            self.opened_file.seek(-1, 1)

# pages reading

    def _read_page_data(self):
        '''Method returns packet data of single page'''
        if self._capture_pattern_not_on_current_position():
            raise CorruptedFileDataError(
                'Missing ogg capture pattern in the beginning of '
                'reading page data. Byte position: ' 
                + str(self.opened_file.tell()))
        temp_ = self.opened_file.read(4)  # capture_pattern

        temp_ += self.opened_file.read(1)  # stream_structure_version
        temp_ += self.opened_file.read(1)  # header_type_flag
        temp_ += self.opened_file.read(8)  # absolute_granule_position
        temp_ += self.opened_file.read(4)  # stream_serial_number
        if len(temp_) != 18:
            raise UnexpectedEndOfFileError()

        page_counter = int.from_bytes(self.opened_file.read(4),
                                      byteorder='little')
        self._packet_pages.append(page_counter)
        if page_counter != self._last_page + 1:
            raise CorruptedFileDataError(
                'Page(s) is(are) missing!\n'
                'Previous last page: ' + str(self._last_page) + '\n'
                'Current page: ' + str(page_counter) + '\n'
                'Current byte position: ' + str(self.opened_file.tell()))
        self._last_page += 1

        temp_ += self.opened_file.read(4)  # page_checksum
        if len(temp_) != 22:
            raise UnexpectedEndOfFileError()

        page_segments_number = self.opened_file.read(1)[0]
        segment_table = self.opened_file.read(page_segments_number)
        if len(segment_table) != page_segments_number:
            raise UnexpectedEndOfFileError()
        segment_table_result = sum(segment_table)

        data = self.opened_file.read(segment_table_result)
        if len(data) < segment_table_result:
            raise UnexpectedEndOfFileError()

        return data

    def _beginning_of_reading_actions(self):
        '''Method does actions in the beginning of the packet reading'''
        self._packet_pages = []
        self._current_packet_data = b''

    def read_packet(self):
        '''Method returns packet data and packet pages'''
        if self._capture_pattern_not_on_current_position():
            self._move_to_page_beginning_above()
            if self._last_page_of_logical_bitstream_reached():
                raise EOFError('File end reached')
            else:
                raise CorruptedFileDataError(
                    'In fact last page is not marked as last '
                    '(in non corrupted part of file data)')

        self._beginning_of_reading_actions()

        self._current_packet_data += self._read_page_data()
        while (not (self._capture_pattern_not_on_current_position()
                    or self._fresh_packet_on_current_page())):
            self._current_packet_data += self._read_page_data()

        return (self._current_packet_data, self._packet_pages)
