from unittest import TestCase
from os import path as os_path

import tests.__init__  # Without this anytask won't see tests
from vorbis.vorbis_main import PacketsProcessor, CorruptedFileDataError


PATH_ORDINARY_TEST_1 = os_path.join(
    os_path.dirname(os_path.abspath(__file__)),
    'test_audiofiles',
    'test_1.ogg')

PATH_TEST_WRONG_OGG_FILE = os_path.join(
    os_path.dirname(os_path.abspath(__file__)),
    'test_audiofiles',
    'test_wrong_ogg_file.ogg')

PATH_TEST_WRONG_VORBIS_FILE = os_path.join(
    os_path.dirname(os_path.abspath(__file__)),
    'test_audiofiles',
    'test_wrong_vorbis_file.ogg')


# noinspection PyMethodMayBeStatic
class PacketsProcessorTests(TestCase):
    def test_ogg_not_vorbis_file(self):
        with self.assertRaises(CorruptedFileDataError) as occurred_err:
            PacketsProcessor(PATH_TEST_WRONG_OGG_FILE)

        self.assertEqual(
            occurred_err.exception.__class__,
            CorruptedFileDataError)

        self.assertEqual(
            occurred_err.exception.args[0],
            "File format is not vorbis: " + PATH_TEST_WRONG_OGG_FILE)

    def test_corrupted_vorbis_file(self):
        with self.assertRaises(CorruptedFileDataError) as occurred_err:
            PacketsProcessor(PATH_TEST_WRONG_VORBIS_FILE).process_headers()

        self.assertEqual(
            occurred_err.exception.__class__,
            CorruptedFileDataError)

        self.assertEqual(len(occurred_err.exception.args), 3)
        self.assertEqual(
            occurred_err.exception.args[0],
            'Identification header is lost')

    def test_process_headers(self):
        packets_processor = PacketsProcessor(PATH_ORDINARY_TEST_1)

        packets_processor.process_headers()

        packets_processor.close_file()

    def test_ident_header_processing(self):
        packets_processor = PacketsProcessor(PATH_ORDINARY_TEST_1)

        packets_processor._data_reader.read_packet()
        packets_processor._data_reader.byte_pointer = 1
        packets_processor.logical_streams = []
        packets_processor.logical_streams.append(
            PacketsProcessor.LogicalStream(0))
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

        logical_stream = packets_processor.logical_streams[0]

        assert logical_stream.audio_channels == 2
        assert logical_stream.audio_sample_rate == 44100
        assert logical_stream.bitrate_maximum == 0
        assert logical_stream.bitrate_nominal == 482872
        assert logical_stream.bitrate_minimum == 0
        assert logical_stream.blocksize_0 == 256
        assert logical_stream.blocksize_1 == 2048

        packets_processor.close_file()
