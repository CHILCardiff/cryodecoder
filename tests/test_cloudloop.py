import cryodecoder
import pandas as pd

timeout = 5 # seconds, timeout interval

if __name__ == "__main__":

    # Load data and give a name to the data column (we don't have other strings)
    cl_data = pd.read_csv("./data/test/cloudloop_example.csv")

    # Create a simple list to store blocks in
    blocks = []

    # Then iterate over the data
    for idx, row in cl_data.iterrows():

        # Parse row
        row_blocks = cryodecoder.parse_hex(row["Payload"])
        for block in row_blocks:
            blocks.append(row_blocks)

    # Do something with 'blocks' array of data
    print(f"Read {len(blocks)} from {len(cl_data)} rows.")