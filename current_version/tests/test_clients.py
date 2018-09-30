import sys
import unittest
import os
import pathmagic
from ogg_vorbis_cs import *
from vorbis.vorbis_main import PacketsProcessor
import subprocess


PATH_ORDINARY_TEST_1 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'ordinary_test_1.ogg')
CS_CLIENT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              os.pardir,
                              'ogg_vorbis_cs.py')


class ConsoleClientTests(unittest.TestCase):
    def test_ident_generation(self):
        packets_processor = PacketsProcessor(PATH_ORDINARY_TEST_1)

        packets_processor._data_reader.read_packet()
        packets_processor._data_reader.byte_pointer = 1
        packets_processor.logical_streams = []
        packets_processor.logical_streams += \
            [PacketsProcessor.LogicalStream(0)]
        packets_processor._process_identification_header()

        assert generate_ident_header(packets_processor.logical_streams[0]) == \
            '''
--------IDENTIFICATION HEADER INFO:

[audio_channels] = 2
    Number of audio channels
[audio_sample_rate] = 44100
    Value of audio sample rate

[bitrate_maximum] = 0
[bitrate_nominal] = 482872
[bitrate_minimum] = 0
    About bitrates values (0 means value is unset):
        * All three fields set to the same value implies a fixed rate,
          or tightly bounded, nearly fixed-rate bitstream
        * Only nominal set implies a VBR or ABR stream
          that averages the nominal bitrate
        * Maximum and or minimum set implies a VBR bitstream
          that obeys the bitrate limits
        * None set indicates the encoder does not care to speculate.

[blocksize_0] = 8
[blocksize_1] = 11
    These two values are 2 exponent. They represents blocksizes of vorbis
    window function\
'''

    def test_comment_generation(self):
        packets_processor = PacketsProcessor(PATH_ORDINARY_TEST_1)

        packets_processor._data_reader.read_packet()
        packets_processor._data_reader.read_packet()
        packets_processor._data_reader.byte_pointer = 1
        packets_processor.logical_streams = []
        packets_processor.logical_streams += \
            [PacketsProcessor.LogicalStream(0)]
        packets_processor._process_comment_header()

        packets_processor.logical_streams[0].comment_header_decoding_failed = \
            False

        assert \
            generate_comment_header(packets_processor.logical_streams[0]) == \
            '''
--------COMMENT HEADER INFO:

[comment_header_decoding_failed] = False
    Indicates if decoder failed while decoding comment header. If 'True' then
    strings below may be damaged, nonsensical at all or just absent.
    Note: strings bigger than 1000 characters will be cut and marked with [...]
    at the end for convenient look
[vendor_string]
    Main comment string. Contains:
        Nothing. String(s) is(are) absent
[user_comment_list_strings]
    User comment strings. May be not set. Contains:
        ALBUM=The Witcher 3: Wild Hunt (GameRip Soundtrack)
        ALBUMARTIST=Marcin Przybyłowicz, Mikolai Stroinski, Percival
        ARTIST=Marcin Przybyłowicz, Mikolai Stroinski, Percival
        COMMENT=VladlenCry\r
http://vk.com/vladlencry\r
\r
Ripped By VladlenCry
        DATE=2015
        DISCNUMBER=2
        GENRE=Soundtrack
        TITLE=CS601 Immortal A
        TRACKNUMBER=110
        COMPOSER=Marcin Przybyłowicz, Percival Schuttenbach
        COVERARTMIME=image/jpeg
        COVERART=/9j/7gAOQWRvYmUAZAAAAAAB/+Ev5EV4aWYAAE1NACoAAAAIAAwBDgACAAAAF\
wAACKoBEgADAAAAAQABAAABGgAFAAAAAQAACMIBGwAFAAAAAQAACMoBKAADAAAAAQACAAA\
BMQACAAAAIgAACNIBMgACAAAAFAAACPQBOwACAAAACwAACQiHaQAEAAAAAQAACRScmwABA\
AAALgAAEVicnQABAAAAFgAAEYbqHAAHAAAIDAAAAJ4AABGcHOoAAAAIAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA[...]\
'''

    def test_console_loading_without_args(self):
        completed_process = \
            subprocess.run([sys.executable,
                            CS_CLIENT_PATH],
                           stdout=subprocess.PIPE)

    def test_console_print_version(self):
        completed_process = \
            subprocess.run([sys.executable,
                            CS_CLIENT_PATH,
                            '--version'],
                           stdout=subprocess.PIPE)

    def test_console_simple_loading_with_standart_headers(self):
        # more tests like that
        completed_process = \
            subprocess.run([sys.executable,
                            CS_CLIENT_PATH,
                            '--headers=ident,setup,comment',
                            PATH_ORDINARY_TEST_1],
                           stdout=subprocess.PIPE)
