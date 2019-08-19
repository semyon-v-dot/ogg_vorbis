from typing import List, BinaryIO, Tuple


class FileDataException(Exception):
    """Root for all ogg_vorbis.py exceptions and errors"""
    pass


class CorruptedFileDataError(FileDataException):
    """Raises when file data is corrupted"""
    pass


class UnexpectedEndOfFileError(CorruptedFileDataError):
    """Raises when end of file unexpectedly reached while data reading"""
    pass


class PacketsReader:
    """Class for reading packets"""
    opened_file: BinaryIO

    _current_packet_data: bytes = b''
    _packet_pages: List[int] = []
    _last_page: int = -1

    def __init__(self, filename: str):
        # This line can cause OSError raising. Occurred exception should be
        # caught by outer code
        self.opened_file = open(filename, 'rb')

        if not self._ogg_capture_pattern_on_current_position():
            raise CorruptedFileDataError(
                'File not an ogg container: ' + filename)

    def read_packet(self) -> Tuple[bytes, List[int]]:
        """Method returns packet data and packet pages"""
        if not self._ogg_capture_pattern_on_current_position():
            self._move_to_page_beginning_above()

            if self._last_page_of_logical_bitstream_reached():
                raise EOFError('File end reached')
            else:
                raise CorruptedFileDataError(
                    'Last page is not marked as last '
                    '(in non corrupted part of file data)')

        self._beginning_of_reading_actions()

        self._current_packet_data += self._read_page_data()
        while (self._ogg_capture_pattern_on_current_position()
               and not self._fresh_packet_on_current_page()):
            self._current_packet_data += self._read_page_data()

        return self._current_packet_data, self._packet_pages

    def _read_page_data(self) -> bytes:
        """Method returns packet data of single page"""
        if not self._ogg_capture_pattern_on_current_position():
            raise CorruptedFileDataError(
                'Missing ogg capture pattern. Byte position: '
                + str(self.opened_file.tell()))

        # capture_pattern
        temp_ = self.opened_file.read(4)

        # stream_structure_version
        temp_ += self.opened_file.read(1)

        # header_type_flag
        temp_ += self.opened_file.read(1)

        # absolute_granule_position
        temp_ += self.opened_file.read(8)

        # stream_serial_number
        temp_ += self.opened_file.read(4)

        if len(temp_) != 18:
            raise UnexpectedEndOfFileError()

        page_counter = int.from_bytes(
            self.opened_file.read(4),
            byteorder='little')
        self._packet_pages.append(page_counter)

        if page_counter != self._last_page + 1:
            raise CorruptedFileDataError(
                'Page(s) is(are) missing!\n'
                'Previous last page: ' + str(self._last_page)
                + '\nCurrent page: ' + str(page_counter)
                + '\nCurrent byte position: ' + str(
                    self.opened_file.tell()))
        self._last_page += 1

        # page_checksum
        temp_ += self.opened_file.read(4)

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
        """Method does actions in the beginning of the packet reading"""
        self._packet_pages.clear()
        self._current_packet_data = b''

    def _last_page_of_logical_bitstream_reached(self) -> bool:
        """Method returns True if fresh packet is on current page"""
        if not self._ogg_capture_pattern_on_current_position():
            raise CorruptedFileDataError(
                'Missing ogg capture pattern. Byte position: '
                + str(self.opened_file.tell()))

        # capture_pattern
        temp_ = self.opened_file.read(4)

        # stream_structure_version
        temp_ += self.opened_file.read(1)

        if len(temp_) != 5:
            raise UnexpectedEndOfFileError()

        header_type_flag = self.opened_file.read(1)[0]
        self.opened_file.seek(-6, 1)

        return (header_type_flag & 4) == 4

    def move_byte_position(self, new_position: int):
        """Moves byte pointer

        Moves byte pointer to [new_position]. In case if [new_position] is
        not a beginning of a packet, method moves byte pointer up until some
        packet beginning is reached"""
        assert new_position >= 0

        self.opened_file.seek(new_position)
        self._current_packet_data = b''
        self._packet_pages = []

        if not (self._ogg_capture_pattern_on_current_position()
                and self._fresh_packet_on_current_page()):

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
        """Moves byte pointer up until a beginning of some page is reached"""
        while not self._ogg_capture_pattern_on_current_position():
            if self.opened_file.tell() == 0:
                raise CorruptedFileDataError(
                    "Capture pattern is missing at the beginning of the file")
            self.opened_file.seek(-1, 1)

    def _fresh_packet_on_current_page(self) -> bool:
        """Method returns True if fresh packet is on current page"""
        if not self._ogg_capture_pattern_on_current_position():
            raise CorruptedFileDataError(
                'Missing ogg capture pattern. Byte position: '
                + str(self.opened_file.tell()))

        # capture_pattern
        temp_ = self.opened_file.read(4)

        # stream_structure_version
        temp_ += self.opened_file.read(1)

        if len(temp_) != 5:
            raise UnexpectedEndOfFileError()

        header_type_flag = self.opened_file.read(1)[0]
        self.opened_file.seek(-6, 1)

        return (header_type_flag & 1) == 0

    def _ogg_capture_pattern_on_current_position(self) -> bool:
        """Checks if capture pattern not on current position

        Returns True if page capture pattern not presented on current byte
        position"""
        capture_pattern = self.opened_file.read(4)

        self.opened_file.seek(-4, 1)

        return capture_pattern == b'OggS'

    def close_file(self):
        """Method closes opened ogg-vorbis file"""
        self.opened_file.close()
