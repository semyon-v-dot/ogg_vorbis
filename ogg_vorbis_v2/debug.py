import sys
import os
from vorbis.codebook import CodebookDecoder
from vorbis.vorbis_main import DataReader
from vorbis.vorbis_main import PacketsProcessor
from vorbis.ogg import PacketsReader

PATH_TEST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'tests', 
                                'ordinary_test_1.ogg')

# packets_processor = PacketsProcessor(PATH_TEST)
# 
# packets_processor.process_headers()
# 
# codebooks = \
#     packets_processor._logical_streams[0].vorbis_codebook_configurations
#     
# for i in range(len(codebooks)):
#     print(codebooks[i][0])

data_reader = DataReader(PATH_TEST)

data_reader.read_packet()

returned_bits = ''
for i in range(len(data_reader._current_packet) * 8):
    returned_bits = str(data_reader.read_bit()) + returned_bits
    
print(returned_bits)
