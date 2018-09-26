from sys import argv
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

    if not hasattr(logical_stream, 'vendor_string') or \
       len(logical_stream.vendor_string) == 0:
        output_ += "        Nothing. String is absent\n"
    elif len(logical_stream.vendor_string) > 1000:
        output_ += "        " + logical_stream.vendor_string[:1000] + \
            "[...]\n"
    else:
        output_ += "        " + logical_stream.vendor_string + "\n"

    output_ += '''\
[user_comment_list_strings]
    User comment strings. May be not set. Contains:
'''
    if not hasattr(logical_stream, 'user_comment_list_strings') or \
       len(logical_stream.user_comment_list_strings) == 0:
        output_ += "        Nothing. Strings are absent"
        return output_
    for string_ in logical_stream.user_comment_list_strings:
        if len(string_) > 1000:
            output_ += "        " + string_[:1000] + "[...]\n"
        else:
            output_ += "        " + string_ + "\n"

    return output_[:-1]


def generate_setup_header(logical_stream):  # WIP
    pass


help = '''\
Usage: ogg_vorbis_cs.py [Options] audiofile

Options:
    --version                   Print program's version number and exit
    -h, --help                  Print this help message and exit
    --headers=[headers_types]   Print specified in [headers_types]
                                headers. 'ident'(identification), 'comment' and
                                'setup' headers are presented. 'ident'
                                and 'comment' headers are printes if this
                                command is absent
'''


if __name__ == '__main__':  # tests
    if len(argv) == 1:
        exit('Try \'ogg_vorbis_cs.py --help\'')
    if argv[1] in ('--help', '-h'):
        exit(help)

    if argv[1] == '--version':
        exit('Current version: ' + '2')

    argv_file_number = 1

    ident_needed = True
    comment_needed = True
    setup_needed = False
    if argv[1][:10] == '--headers=':
        ident_needed = comment_needed = setup_needed = False
        ident_needed = 'ident' in argv[1]
        comment_needed = 'comment' in argv[1]
        setup_needed = 'setup' in argv[1]

        argv_file_number += 1

    packets_processor = PacketsProcessor(argv[argv_file_number])
    packets_processor.process_headers()

    if ident_needed:
        print(generate_ident_header(packets_processor.logical_streams[0]))
    if comment_needed:
        print(generate_comment_header(packets_processor.logical_streams[0]))
    if setup_needed:
        print(generate_setup_header(packets_processor.logical_streams[0]))
