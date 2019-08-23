def ilog(x: int) -> int:
    """Returns number of the highest set bit

    Two’s complement integer value [x] used"""
    if x <= 0:
        return 0

    return_value = 0
    while x > 0:
        return_value += 1
        x >>= 1

    return return_value


def float32_unpack(x: int) -> float:
    """Unpacks float32 from Vorbis binary

    Method translates the packed binary representation of a Vorbis codebook
    float value into the representation used by the decoder for floating
    point numbers"""
    mantissa = x & 0x1fffff
    sign = x & 0x80000000
    exponent = (x & 0x7fe00000) >> 21

    assert sign >= 0 and mantissa >= 0 and exponent >= 0

    if sign != 0:
        mantissa *= -1

    return float(mantissa) * pow(2, exponent - 788)


def lookup1_values(codebook_entries: int, codebook_dimensions: int) -> int:
    """Helper function for lookup table of lookup type 1

    Computes the correct length of the value index for a codebook VQ
    lookup table of lookup type 1"""
    return_value: int = 0

    while return_value ** codebook_dimensions <= codebook_entries:
        return_value += 1

    return return_value - 1


def bit_reverse(n: int) -> int:
    """Reverses first 32 bits in number. Leading bits are cut off"""
    assert n >= 0

    n = ((n & 0xAAAAAAAA) >> 1) | ((n & 0x55555555) << 1)
    n = ((n & 0xCCCCCCCC) >> 2) | ((n & 0x33333333) << 2)
    n = ((n & 0xF0F0F0F0) >> 4) | ((n & 0x0F0F0F0F) << 4)
    n = ((n & 0xFF00FF00) >> 8) | ((n & 0x00FF00FF) << 8)

    return ((n >> 16) | (n << 16)) & ((1 << 32) - 1)
