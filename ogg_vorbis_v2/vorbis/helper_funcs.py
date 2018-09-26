def shorter_attribute_creation(func):
    '''Decorator shorten function attributes creation'''
    def wrapped(*args, **kwargs):
        return func(wrapped, *args, **kwargs)
    return wrapped


def ilog(x):
    '''Function returns the position number of the highest set bit in the \
two’s complement integer value [x]'''
    if x <= 0:
        return 0

    return_value = 0
    while x > 0:
        return_value += 1
        x >>= 1

    return return_value


def float32_unpack(x):
    '''Method translates the packed binary representation of a Vorbis \
codebook float value into the representation used \
by the decoder for floating point numbers'''
    mantissa = x & 0x1fffff
    sign = x & 0x80000000
    exponent = (x & 0x7fe00000) >> 21
    if sign < 0 or mantissa < 0 or exponent < 0:
        raise ValueError('Float32 unpacking failed. '
                         'Mantissa/sign/exponent is not unsigned')

    if sign:
        mantissa *= -1

    return mantissa * pow(2, exponent - 788)


def lookup1_values(codebook_entries, codebook_dimensions):
    '''Function compute the correct length of the value index \
for a codebook VQ lookup table of lookup type 1'''
    return_value = 0

    while (return_value ** codebook_dimensions) <= codebook_entries:
        return_value += 1

    return return_value - 1
