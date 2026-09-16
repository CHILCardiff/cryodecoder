import cryodecoder.parser
import pandas as pd
import time

timeout = 5 # seconds, timeout interval

if __name__ == "__main__":

    # Load data and give a name to the data column (we don't have other strings)
    cl_data = pd.read_csv("./data/test/cloudloop_example.csv")

    # Create a simple list to store blocks in
    blocks = []

    # Then iterate over the data
    for idx, row in cl_data.iterrows():

        # In this example, it's saved in hexadecimal format
        byte_data = bytes.fromhex(row["Payload"])

        # Create a parser object
        parser = cryodecoder.parser.Parser()
        parser.push(byte_data)

        while not parser.complete():
            print(f"Buffer: ", parser._buffer)
            parser.update()

        while parser.available():
            print(f"Block found at row {idx}")
            _, block = parser.read()
            print(block)
            blocks.append(block)

    # Do something with 'blocks' array of data
    print(f"Read {len(blocks)} from {len(cl_data)} rows.")