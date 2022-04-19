from kh_common.crc import CRC
import pytest


@pytest.mark.parametrize(
	'crc, value, expected',
	[
		(CRC(), b'test', 0x338bcfac),
		(CRC(40, 0x0004820009, 0x0), b'test', 0x19f6c7a623),
		(CRC(48, 0x8000000000ed), b'test', 0x805fc11fc8ce),
		(CRC(64, 0x42f0e1eba9ea3693), b'test', 0xdeeec356f8c2a93e),
	]
)
def test_crc(crc: CRC, value: bytes, expected: int) :
	assert crc(value) == expected
