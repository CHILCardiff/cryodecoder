import datetime
import logging
from os import PathLike
from sys import stdout
from typing import Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(stdout))

from cryodecoder.parser import Parser, CSVLogger
from cryodecoder.cloudloop import download_records_from_cloudloop, DateLike, DEFAULT_API_ROOT

def parse_hex(hex_input : str):
    """
    Parse CHIL data from hexadecimal strings.

    :param hex_input: String encoding binary data in CHIL format.
    :return: Ordered list of the decoded blocks from the string
    :rtype: list[cryodecoder.blocks.Block]
    
    """
    # Create a parser object
    parser = Parser()
    parser.push(bytes.fromhex(hex_input))

    # Run the parser
    while not parser.complete():
        parser.update()

    # Return the parsed blocks
    #   ...because we're parsing from a string we don't care about the 
    #   timestamp that comes from the Parser object so we can do some 
    #   reformating...
    return [block for timestamp, block in parser._blocks]

def download_and_parse_cloudloop(
    raw_path : str | PathLike,
    data_path : str | PathLike,
    start_date : Optional[DateLike] = None,
    end_date : Optional[DateLike] = None,
    request_params : Optional[dict] = None,
    api_key : Optional[str] = None,
    api_root : str = DEFAULT_API_ROOT,
    disable_progress_bar = False
):

    # Setup CSVLogger
    csv_logger = CSVLogger(data_path)

    # Define a local hook for downloading
    def csv_log_hook(record):
        timestamp = datetime.datetime.fromisoformat(record["at"]) 
        blocks = parse_hex(record["message"])
        for block in blocks:
            csv_logger.logCSV(timestamp, block)
    
    # Download dataframe
    download_records_from_cloudloop(
        raw_path,
        start_date=start_date,
        end_date=end_date,
        request_params=request_params,
        api_key=api_key,
        api_root=api_root,
        disable_progress_bar=disable_progress_bar,
        record_hook=csv_log_hook
    )
