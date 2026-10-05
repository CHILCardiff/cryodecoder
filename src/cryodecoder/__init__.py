from cryodecoder.parser import Parser

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
    """
    Download data from Cloudloop to a .csv file and decode CHIL data from any messages into a separate .csv file.

    :param raw_path: Path for the raw data and metadata from Cloudloop to be downloaded to.
    :type: raw_path: str or cryodecoder.blocks.PathLike
    :param data_path: Path for the parsed CHIL blocks to be written to in .csv format. 
    :type data_path: str or PathLike
    :param start_date: (optional) Messages received after this value will be downloaded.
    :type start_date: Optional[DateLike]
    :param end_date: (optional) Messaged received before this value will be downloaded. If not supplied, it defaults to the current time in UTC.
    :type end_date: Optional[DateLike]
    :param request_params: (optional) Additional parameters to be suppled in the HTTP request.
    :type request_params: Optional[dict]
    :param api_key: (optional) The API key associated with your Cloudloop account. If no api_key is provided, then the function will check for environment variable "CLOUDLOOP_API".
    :type api_key: Optional[str]
    :param api_root: (optional) If another server is used to host the Cloudloop API then the root URL can be changed with this parameter.
    :type api_root: str = DEFAULT_API_ROOT,
    :param disable_progress_bar: (optional) Set to True to disable the CLI progress bar while downloading takes place.
    :type disable_progress_bar: bool
    :return: Ordered list of the decoded blocks from the string
    :rtype: list[cryodecoder.blocks.Block]
    """

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
