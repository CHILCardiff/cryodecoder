import pytest

import cryodecoder, cryodecoder.cloudloop
import pandas 
import logging
import tempfile

def test_download_from_cloudloop():

    with tempfile.NamedTemporaryFile(mode="w+") as tmp:
        tmp.close()
        n_records = cryodecoder.cloudloop.download_records_from_cloudloop(
            output_path = tmp.name,
            start_date = "2026-10-04 00:00:00"
        )
        df = pandas.read_csv(tmp.name)
        assert len(df) == n_records

# import cryodecoder
# import pandas as pd

# timeout = 5 # seconds, timeout interval

# if __name__ == "__main__":

#     # Load data and give a name to the data column (we don't have other strings)
#     cl_data = pd.read_csv("./data/test/cloudloop_example.csv")

#     # Create a simple list to store blocks in
#     blocks = []

#     # Then iterate over the data
#     for idx, row in cl_data.iterrows():

#         # Parse row
#         row_blocks = cryodecoder.parse_hex(row["Payload"])
#         for block in row_blocks:
#             blocks.append(row_blocks)

#     # Do something with 'blocks' array of data
#     print(f"Read {len(blocks)} from {len(cl_data)} rows.")