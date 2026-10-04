import base64
import datetime
import logging
import numpy as np
import pandas
import pathlib 
import requests
import time 
import tqdm

from os import environ, PathLike
from typing import Union, Optional
from types import NoneType

from cryodecoder import logger

DEFAULT_API_ROOT = "https://api.cloudloop.com"
"""
The default URL to pass Cloudloop requests to.
"""

type DateLike = Union[str, datetime.datetime, np.datetime64]
"""
Defines a type for date-like objects for checking start/end date inputs
"""

def is_datelike(date) -> bool:
    """
    Validates an object to see if it is DateLike
    """
    # Check whether we have a datetime object
    if isinstance(date, (np.datetime64, datetime.datetime)):
        return True
    elif isinstance(date, str):
        try:
            datetime.date.fromisoformat(date)
            return True
        except ValueError:
            try:
                datetime.datetime.fromisoformat(date)
                return True
            except ValueError:
                raise
    else:
        return False

def get_env_api_key():
    if "CLOUDLOOP_API" in environ:
        return environ["CLOUDLOOP_API"]
    else:
        raise KeyError("No API key ('CLOUDLOOP_API') defined in environment variables.")

def __validate_api_parameters(
    request_params : Optional[dict] = None,
    api_key : Optional[str] = None,
    api_root : str = DEFAULT_API_ROOT
):

    # Get API parameters
    if request_params is None:
        request_params = dict()
    elif not isinstance(request_params, dict):
        raise ValueError("request_params argument should be a dictionary of name : value arguments to pass with the API request")

    # Default API key to the environment variable if it is None
    api_key = api_key or get_env_api_key()

    # Set API key in request parameters if not provided as a token field already
    if not "token" in request_params:
        request_params["token"] = api_key

    # TODO: validate api_root

    return request_params, api_key, api_root

def list_records_from_cloudloop(
    start_date : Optional[DateLike] = None,
    end_date : Optional[DateLike] = None,
    request_params : Optional[dict] = None,
    api_key : Optional[str] = None,
    api_root : str = DEFAULT_API_ROOT,
    disable_progress_bar : bool = True
): 
    """
    Downloads message records from Cloudloop between specified dates and returns them in a Pandas DataFrame object.
    
    [TODO: Add further description, arguments and return information.]
    """

    if start_date is None:
        start_date = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
    if end_date is None:
        end_date = datetime.datetime.now(tz=datetime.UTC)

    # Validate datetimes 
    datelike_error = "{var_name} should be a string representation of the date (IS0 8601, YYYY-mm-DD HH:MM:SS), a datetime.datetime object or a numpy datetime64 object."
    if not is_datelike(start_date):
        raise TypeError(datelike_error.format(var_name="start_date"))
    else:
        # Convert to datetime
        start_date = pandas.to_datetime(start_date)
    if not is_datelike(end_date):
        raise TypeError(datelike_error.format(var_name="end_date"))
    else:
        # Convert to datetime
        end_date = pandas.to_datetime(end_date)

    # Validate params users in API request
    request_params, api_key, api_root = \
        __validate_api_parameters(request_params, api_key, api_root)

    # Get a record of all the messages within the current date range
    iso_datetime_format = "%Y-%m-%dT%H:%M:%S"

    # Setup request URL
    path_request_records = "{api_root}/Data/GetMessageRecords?from={start_date}&to={end_date}".format(
        api_root   = api_root,
        start_date = start_date.strftime(iso_datetime_format),
        end_date   = end_date.strftime(iso_datetime_format),
    )

    logger.info(f"Starting request to {path_request_records}")
    # Perform request
    records_response = requests.get(
        path_request_records, 
        params=request_params
    )
    logger.info(f"Finished request to {path_request_records}")

    # and check that it succeeded
    if records_response.status_code != 200:
        raise requests.ConnectionError(f"Could not download message (HTTP code: {records_response.status_code})")

    # Extract the data from the json object
    records = records_response.json()["messageRecords"]
    logger.info(f"Retrieved {len(records)} records from response.")

    # S
    CLOUDLOOP_REQUIRED_KEYS = [
        "id", "account", "thing", "at", "direction", "pulseRecord", "size", "type", "snippet", "category", "fileType", "transport", "deliveryFailure", "decodedTypes"
    ]

    # Store the records in a DataFrame
    logger.info(f"Converting records to pandas.DataFrame...")

    # Setup dictionary to store arrays of data
    data = {key : [] for key in CLOUDLOOP_REQUIRED_KEYS}

    # We time this operation as a it was previously a performance bottleneck
    # when creating the DataFrame with row-by-row concatenation.
    tstart = time.time()
    for record in tqdm.tqdm(
        records, 
        ascii="Compiling records for dataframe...", 
        disable=disable_progress_bar
    ):

        # Make dict of data with data in lists to DF compatability
        for key in CLOUDLOOP_REQUIRED_KEYS:
            # this will raise a KeyError if there key isn't available in the
            # record
            data[key].append(record[key])

    # Append new row
    records_df = pandas.DataFrame(data=data)

    tend = time.time()
    logger.info(f"Converted records to DataFrame in {tend - tstart}")
    logger.info(f"Finished converting records to pandas.DataFrame...")

    return records_df

class LingoMOMessage:

    def __init__(self,
        id : str,
        received_at : DateLike | str,
        identity : dict, 
        message : bytes,
        raw : Optional[dict] = None
    ):
        self.id = id
        self.received_at = pandas.to_datetime(received_at)
        self.identity  = identity
        self.message = message

        # Assign identity parameters
        if not "thingId" in identity:
            raise KeyError("thingId missing from LingoMO record.")
        
        self.thing_id = identity["thingId"]
        self.groups = []
        if "thingGroup" in identity:
            for group in identity["thingGroup"]:
                self.groups.append(group)

        if "imei" in identity["hardware"]:
            self.imei = identity["hardware"]["imei"]

        if "serial" in identity["hardware"]:
            self.serial = identity["hardware"]["serial"]

        self.raw = raw or None

    @staticmethod
    def from_dict(data):

        for key in ("id", "receivedAt", "identity", "message"):
            if not "id" in data:
                raise KeyError("LingoMO data missing required key 'id'")

        # Convert datetime
        received_at_datetime = datetime.datetime(
            data["receivedAt"]["year"],
            data["receivedAt"]["month"],
            data["receivedAt"]["day"],
            data["receivedAt"]["hour"],
            data["receivedAt"]["minute"],
            data["receivedAt"]["second"]
        )

        # Define a base constructor across SBD message types
        base_constructor = {
            "id"          : data["id"],
            "received_at" : received_at_datetime,
            "identity"    : data["identity"],
            "message"     : base64.b64decode(data["message"]),
            "raw"         : data
        }

        if "sbd" in data:
            return LingoMOMessageSBD(**base_constructor)
        elif "cellular" in data:
            logger.warning("Additional parsing of LingoMO cellular messages is not supported, a LingoMOMessage object will be returned.")
            return LingoMOMessage(**base_constructor)
        elif "imt" in data:
            logger.warning("Additional parsing of LingoMO IMT messages is not supported, a LingoMOMessage object will be returned.")
            return LingoMOMessage(**base_constructor)

class LingoMOMessageSBD(LingoMOMessage):

    def __init__(self, **kwargs):
        # Call super instructor
        super().__init__(**kwargs)

        if self.raw is None:
            return self

        # Get position information
        lat = None; long = None
        if "location" in self.raw["sbd"]:
            loc = self.raw["sbd"]["location"]
            if "latitude" in loc:
                lat = loc["latitude"]
            if "longitude" in loc:
                lat = loc["longitude"]

        # Assign latitude and longitude
        self.latitude = lat
        self.longitude = long
    

def get_message_from_cloudloop(
    record : str, 
    request_params : Optional[dict] = None,
    api_key : Optional[str] = None,
    api_root : str = DEFAULT_API_ROOT
):
    if request_params is None:
        request_params = dict()

    # Default API key to the environment variable if it is None
    api_key = api_key or get_env_api_key()
    
    if not "token" in request_params:
        request_params["token"] = api_key

    # Generate API URL 
    message_url="{api_root}/Data/GetLingoMo?messageRecord={record_id}".format(
        record_id = record, 
        api_root  = api_root
    )
    # Make request
    message_response = requests.get(message_url, params=request_params)
    
    if message_response.status_code != 200:
        raise requests.ConnectionError(f"Could not download message (HTTP code: {message_response.status_code})")

    return LingoMOMessage.from_dict(message_response.json())

def download_records_from_cloudloop(
    output_path : str | PathLike,
    start_date : Optional[DateLike] = None,
    end_date : Optional[DateLike] = None,
    request_params : Optional[dict] = None,
    api_key : Optional[str] = None,
    api_root : str = DEFAULT_API_ROOT
):
    
    # Parse input arguments
    if not isinstance(output_path, str | PathLike):
        raise TypeError("output_path should be a string or PathLike object poiintng to ")
    
    dataframe = list_records_from_cloudloop(
        start_date=start_date,
        end_date=end_date,
        request_params=request_params,
        api_key=api_key,
        api_root=api_root
    )

    dataframe.reset_index(inplace=True)
    dataframe.drop(columns=["index",])

    # Add optional columns
    dataframe["message"] = ""
    dataframe["imei"] = ""
    dataframe["serial"] = ""
    dataframe["latitude"] = np.nan
    dataframe["longitude"] = np.nan

    # Write file
    output_path = pathlib.Path(output_path)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True)

    # Iterate over rows in Dataframe
    for idx in tqdm.trange(len(dataframe)):
        row = dataframe.iloc[idx]

        # Download record from cloudloop
        logger.debug(f"Downloading record {row["id"]} from {row["at"]}")
        record = get_message_from_cloudloop(
            row["id"],
            request_params=request_params,
            api_key=api_key,
            api_root=api_root 
        )

        # Append data
        dataframe.loc[idx, "message"] = record.message.hex()
        dataframe.loc[idx, "imei"] = record.imei
        if record.serial is not None:
            dataframe.loc[idx, "serial"] = record.serial
        if record.latitude is not None:
            dataframe.loc[idx, "latitude"] = record.latitude
        if record.longitude is not None:
            dataframe.loc[idx, "longitude"] = record.longitude

        if idx == 0:
            dataframe[dataframe.index == idx].to_csv(output_path, mode="w", index=False)
        else:
            dataframe[dataframe.index == idx].to_csv(output_path, mode="a", header=False, index=False)

    logger.info(f"Finished writing records to {output_path}")
    return len(dataframe)
