from unittest import TestCase, main as unittest_main
from os import pardir as os_pardir, remove as os_remove
from os.path import (
    join as os_path_join,
    dirname as os_path_dirname,
    abspath as os_path_abspath,
    exists as os_path_exists)
from sys import path as sys_path
from urllib.request import urlopen
from shutil import copyfileobj as shutil_copyfileobj

sys_path.append(os_path_join(
    os_path_dirname(os_path_abspath(__file__)),
    os_pardir))

from vorbis.vorbis_main import PacketsProcessor, CorruptedFileDataError


TEST_FILE_1_PATH = os_path_join(
    os_path_dirname(os_path_abspath(__file__)),
    'test_audiofiles',
    'test_1.ogg')

TEST_FILE_NOT_OGG_PATH = os_path_join(
    os_path_dirname(os_path_abspath(__file__)),
    'test_audiofiles',
    'test_wrong_ogg_file.ogg')

TEST_FILE_NOT_VORBIS_PATH = os_path_join(
    os_path_dirname(os_path_abspath(__file__)),
    'test_audiofiles',
    'test_wrong_vorbis_file.ogg')

TEST_FILE_NOT_OGG_URL: str = (
    r'https://raw.githubusercontent.com/susimus/ogg_vorbis/master/tests'
    r'/test_audiofiles/test_wrong_ogg_file.ogg')

TEST_FILE_NOT_VORBIS_URL: str = (
    r'https://raw.githubusercontent.com/susimus/ogg_vorbis/master/tests'
    r'/test_audiofiles/test_wrong_vorbis_file.ogg')

TEST_FILE_1_URL: str = (
    r'https://raw.githubusercontent.com/susimus/ogg_vorbis/master/'
    r'tests/test_audiofiles/test_1.ogg')

test_file_not_ogg_was_downloaded: bool = False
test_file_not_vorbis_was_downloaded: bool = False
test_file_1_was_downloaded: bool = False


# noinspection PyPep8Naming
def setUpModule():
    global TEST_FILE_1_PATH, TEST_FILE_NOT_OGG_PATH, TEST_FILE_NOT_VORBIS_PATH

    if not os_path_exists(TEST_FILE_1_PATH):
        global test_file_1_was_downloaded, TEST_FILE_1_URL

        test_file_1_was_downloaded = True

        with urlopen(TEST_FILE_1_URL) as response, (
                open(TEST_FILE_1_PATH, 'wb')) as out_file:
            shutil_copyfileobj(response, out_file)

    if not os_path_exists(TEST_FILE_NOT_OGG_PATH):
        global test_file_not_ogg_was_downloaded, TEST_FILE_NOT_OGG_URL

        test_file_not_ogg_was_downloaded = True

        with urlopen(TEST_FILE_NOT_OGG_URL) as response, (
                open(TEST_FILE_NOT_OGG_PATH, 'wb')) as out_file:
            shutil_copyfileobj(response, out_file)

    if not os_path_exists(TEST_FILE_NOT_VORBIS_PATH):
        global test_file_not_vorbis_was_downloaded, TEST_FILE_NOT_VORBIS_URL

        test_file_not_vorbis_was_downloaded = True

        with urlopen(TEST_FILE_NOT_VORBIS_URL) as response, (
                open(TEST_FILE_NOT_VORBIS_PATH, 'wb')) as out_file:
            shutil_copyfileobj(response, out_file)


# noinspection PyPep8Naming
def tearDownModule():
    global test_file_1_was_downloaded
    global test_file_not_ogg_was_downloaded
    global test_file_not_vorbis_was_downloaded

    if test_file_1_was_downloaded:
        global TEST_FILE_1_PATH

        os_remove(TEST_FILE_1_PATH)

    if test_file_not_ogg_was_downloaded:
        global TEST_FILE_NOT_OGG_PATH

        os_remove(TEST_FILE_NOT_OGG_PATH)

    if test_file_not_vorbis_was_downloaded:
        global TEST_FILE_NOT_VORBIS_PATH

        os_remove(TEST_FILE_NOT_VORBIS_PATH)


# noinspection PyMethodMayBeStatic
class PacketsProcessorTests(TestCase):
    def test_ogg_not_vorbis_file(self):
        with self.assertRaises(CorruptedFileDataError) as occurred_err:
            PacketsProcessor(TEST_FILE_NOT_OGG_PATH)

        self.assertEqual(
            occurred_err.exception.__class__,
            CorruptedFileDataError)

        self.assertEqual(
            occurred_err.exception.args[0],
            "File format is not vorbis: " + TEST_FILE_NOT_OGG_PATH)

    def test_corrupted_vorbis_file(self):
        with self.assertRaises(CorruptedFileDataError) as occurred_err:
            PacketsProcessor(TEST_FILE_NOT_VORBIS_PATH).process_headers()

        self.assertEqual(
            occurred_err.exception.__class__,
            CorruptedFileDataError)

        self.assertEqual(2, len(occurred_err.exception.args))
        self.assertEqual(
            occurred_err.exception.args[0],
            'Identification header is lost')

    def test_process_headers(self):
        packets_processor = PacketsProcessor(TEST_FILE_1_PATH)

        packets_processor.process_headers()

        packets_processor.close_file()

    def test_ident_header_processing(self):
        packets_processor = PacketsProcessor(TEST_FILE_1_PATH)

        packets_processor._data_reader.read_packet()
        packets_processor._data_reader.byte_pointer = 1
        packets_processor.logical_stream = (
            PacketsProcessor.LogicalStreamData(0))
        packets_processor._process_identification_header()

        # test_1.ogg, ident header packet
        #
        #                                           01 76 6F 72
        # 62 69 73 00 | 00 00 00 02 | 44 AC 00 00 | 00 00 00 00
        # 38 5E 07 00 | 00 00 00 00 | B8 01
        #
        # 01
        # 76 6F 72 62 . 69 73
        # 00 00 00 00
        # 02
        # 44 AC 00 00
        # 00 00 00 00
        # 38 5E 07 00
        # 00 00 00 00
        # B8
        # 01
        #
        # Header type. It's ident header
        # 01
        #
        # It's 'vorbis', header sync pattern
        # 76 6F 72 62 . 69 73
        #
        # Vorbis I version
        # 00 00 00 00
        #
        # Audio channels
        # 02
        #
        # audio_sample_rate
        # HEX: 44 AC 00 00
        # BIN: 0 | 0 | 1010 1100 | 0100 0100
        # DEC: 44100
        #
        # bitrate_maximum
        # 00 00 00 00
        #
        # bitrate_nominal
        # HEX: 38 5E 07 00
        # BIN: 0 | 0 0111 | 0101 1110 | 0011 1000
        # DEC: 482872
        #
        # bitrate_minimum
        # 00 00 00 00
        #
        # blocksize_0 (2 exponent of that value)
        # 8
        #
        # blocksize_1 (2 exponent of that value)
        # B
        #
        # Framing bit. Should be '1'
        # 01

        logical_stream = packets_processor.logical_stream

        assert logical_stream.audio_channels == 2
        assert logical_stream.audio_sample_rate == 44100
        assert logical_stream.bitrate_maximum == 0
        assert logical_stream.bitrate_nominal == 482872
        assert logical_stream.bitrate_minimum == 0
        assert logical_stream.blocksize_0 == 256
        assert logical_stream.blocksize_1 == 2048

        packets_processor.close_file()


if __name__ == '__main__':
    unittest_main()
