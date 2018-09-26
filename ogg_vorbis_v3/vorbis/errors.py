_counter = 1


def _init():
    global _counter

    _counter += 1
    return _counter - 1

# WIP # Make comments for errors


ERROR_FILE_FORMAT_NOT_VORBIS = _init()
ERROR_FILE_FORMAT_NOT_OGG = _init()
ERROR_INCORRECT_FILE_NAME = _init()
ERROR_CORRUPTED_FILE_DATA_BEGINNING = _init()

ERROR_HEADER_SYNC_PATTERN_IS_ABSENT = _init()
ERROR_IDENTIFICATION_HEADER_IS_LOST = _init()
ERROR_COMMENT_HEADER_IS_LOST = _init()
ERROR_SETUP_HEADER_IS_LOST = _init()

ERROR_CODEBOOK_SYNC_PATTERN_IS_ABSENT = _init()
ERROR_CODEBOOK_LENGTHS_INCORRECT_CODING = _init()
ERROR_CODEBOOK_SINGLE_ENTRY = _init()

ERROR_HUFFMAN_TREE_IS_UNDERSPECIFIED = _init()
ERROR_HUFFMAN_TREE_IS_OVERSPECIFIED = _init()

ERROR_MISSING_PAGE = _init()
ERROR_MISSING_OGG_CAPTURE_PATTERN = _init()
