import pytest
import cryodecoder
import cryodecoder.parser

def test_read_file():

    with open("data/childata_cryoeggonly.log", "rb") as fh_cryoegg:

        parser = cryodecoder.read_file(fh_cryoegg)

    assert len(parser.blocks) == 3

    