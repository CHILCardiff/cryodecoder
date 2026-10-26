Decoding \*.log files
========================
The cryodecoder library can also be used to parse `.log` files from CHIL dataloggers into a `*.csv` format for easier data manipulation. This page describes the steps required to do achieve this.

Instructions
------------

.. important:: 
    These instructions assume you have followed the `setup instructions <setup>`__ If you installed cryodecoder to a `virtual environment <https://docs.python.org/3/library/venv.html>`__ then make sure it is activated before continuing.

    To activate the virtual environment on a Windows PC, navigate to the folder and use the shell command below. Replace ``.env`` with the name of the folder containing your virtual environment.

    .. code-block::

        .\.env\Scripts\activate
        
1.  After activating the virtual environment with cryodecoder installed, navigate to the path containing your data.

2.  
    Run cryodecoder in *file* mode to decode the raw ``.log`` file to ``.csv``.

    .. code-block:: shell

        cryodecoder file -i childata.log -i childata.csv

    The ``-i`` and ``-o`` flags are used to pass the input filename and output filename respectively.

3.  Once the file has finished decoding, it will show a message with the total number of packets (blocks) decoded. A summary of the top-level blocks decoded will also be displayed.

.. figure:: /_static/file_decoder.png

    Example commands to decode ``*.log`` files from CHIL dataloggers.

See :ref:`csvfile` for more information on the format of the decoded CSV file. If you wish to interrogate the raw data in more detail, we recommend using the Python API which is described :ref:`here <api_reference>`.