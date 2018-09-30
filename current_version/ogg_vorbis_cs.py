from argparse import ArgumentParser
from vorbis.vorbis_main import PacketsProcessor


def generate_ident_header(logical_stream):  # tests
    '''Function generate identification header from input [logical_stream] \
internal values'''
    return '''
--------IDENTIFICATION HEADER INFO:

[audio_channels] = {}
    Number of audio channels
[audio_sample_rate] = {}
    Value of audio sample rate

[bitrate_maximum] = {}
[bitrate_nominal] = {}
[bitrate_minimum] = {}
    About bitrates values (0 means value is unset):
        * All three fields set to the same value implies a fixed rate,
          or tightly bounded, nearly fixed-rate bitstream
        * Only nominal set implies a VBR or ABR stream
          that averages the nominal bitrate
        * Maximum and or minimum set implies a VBR bitstream
          that obeys the bitrate limits
        * None set indicates the encoder does not care to speculate.

[blocksize_0] = {}
[blocksize_1] = {}
    These two values are 2 exponent. They represents blocksizes of vorbis
    window function\
'''.format(
        logical_stream.audio_channels,
        logical_stream.audio_sample_rate,
        logical_stream.bitrate_maximum,
        logical_stream.bitrate_nominal,
        logical_stream.bitrate_minimum,
        logical_stream.blocksize_0,
        logical_stream.blocksize_1)


def generate_comment_header(logical_stream):  # tests
    '''Function generate comment header from input [logical_stream] \
internal values'''
    output_ = '''
--------COMMENT HEADER INFO:

[comment_header_decoding_failed] = {}
    Indicates if decoder failed while decoding comment header. If 'True' then
    strings below may be damaged, nonsensical at all or just absent.
    Note: strings bigger than 1000 characters will be cut and marked with [...]
    at the end for convenient look
[vendor_string]
    Main comment string. Contains:
'''.format(logical_stream.comment_header_decoding_failed)
        
    output_ += _process_comment_lines(logical_stream, 'vendor_string')
    output_ += '''\
[user_comment_list_strings]
    User comment strings. May be not set. Contains:
'''
    output_ += \
        _process_comment_lines(logical_stream, 'user_comment_list_strings')

    return output_[:-1]

    
def _process_comment_lines(logical_stream, lines_name):
    if not hasattr(logical_stream, lines_name) or \
       len(getattr(logical_stream, lines_name)) == 0:
        return "        Nothing. String(s) is(are) absent\n"
    
    lines = getattr(logical_stream, lines_name)
    if type(lines) == str:
        lines = [lines]
    output_ = ''

    for line_ in lines:
        if len(line_) > 1000:
            output_ += "        " + line_[:1000] + "[...]\n"
        else:
            output_ += "        " + line_ + "\n"
            
    return output_


def generate_setup_header(logical_stream):  # WIP
    pass


CURRENT_VERSION = 'ogg_vorbis 3'


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Process .ogg audiofile with vorbis coding and '
                    'output headers data')

    parser.add_argument(
        '--version', 
        help="print program's current version number",
        action='version',
        version=CURRENT_VERSION)
    
    parser.add_argument(
        '--headers', 
        help="stores string (without spaces) with names of headers for output.\
 'ident'(identification), 'comment' and 'setup' headers are presented. \
Default value: 'ident,comment' - so 'ident' and 'comment' headers are printes \
if this argument is absent",
        default='ident,comment')
    
    parser.add_argument(
        'filepath', 
        help='path to file which will be processed',
        type=str)

    args = parser.parse_args()
        
    packets_processor = PacketsProcessor(args.filepath)
    packets_processor.process_headers()
    
    if 'ident' in args.headers:
        print(generate_ident_header(packets_processor.logical_streams[0]))
    if 'comment' in args.headers:
        print(generate_comment_header(packets_processor.logical_streams[0]))
    if 'setup' in args.headers:
        print(generate_setup_header(packets_processor.logical_streams[0]))
