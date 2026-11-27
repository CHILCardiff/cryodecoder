import pytest

import cryodecoder, cryodecoder.cloudloop, cryodecoder.parser
import pandas 
import pathlib
import logging
import tempfile

def test_download_from_cloudloop():

    with tempfile.NamedTemporaryFile(mode="w+") as tmp:
        tmp.close()
        n_records = cryodecoder.cloudloop.download_records_from_cloudloop(
            output_path = tmp.name,
            start_date = "2026-10-04 00:00:00",
            end_date = "2026-10-04 04:00:00"
        )
        df = pandas.read_csv(tmp.name)
        assert len(df) == n_records

def test_download_and_parse_from_cloudloop():

    with \
        tempfile.NamedTemporaryFile(mode="w+") as tmp1, \
        tempfile.NamedTemporaryFile(mode="w+") as tmp2:

        # Close files so they can be written to
        tmp1.close(); tmp2.close()
        # Download records from cloudloop
        n_records = cryodecoder.download_and_parse_cloudloop(
            raw_path = tmp1.name,
            data_path = tmp2.name,
            start_date = "2026-10-04 00:00:00",
            end_date = "2026-10-04 04:00:00"
        )
        df = pandas.read_csv(tmp1.name)
        # Check that the number of records written to the log match
        # the number downloaded.
        assert len(df) == n_records

def test_csv_log_hook(caplog):

    with tempfile.NamedTemporaryFile(mode="w+") as tmp1:
        # Close file to allow for access with CSVLogger
        tmp1.close()
        with cryodecoder.parser.CSVLogger(tmp1.name) as csv_logger:

            # Create fake test dataframe
            df_fake = pandas.DataFrame(
                data = {
                    "at" : ["2026-10-04 04:00:00",],
                    "message" : ["Invalid block!",]
                }
            )

            cryodecoder.__csv_log_hook(csv_logger, df_fake.iloc[0])

            assert "Error decoding message" in caplog.text
        
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