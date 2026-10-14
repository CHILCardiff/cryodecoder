Serial decoding (USB)
=====================
The cryodecoder library decodes and logs packets from CHIL dataloggers connected to a computer via a serial (USB) connection. It runs in a terminal (command line) window and performs the following tasks:

* Display **real-time updates** from the on-board datalogger sensors.
* **Save raw data** from received packets.
* Process and save **decoded packets** from Cryowurst and Cryoegg instruments.
* **Log status and debugging data** from the receiver to a local file.

The rest of this page describes the steps to run the serial decoder and interpet output the command line.

Instructions
-------------

Connect to the datalogger
^^^^^^^^^^^^^^^^^^^^^^^^^
Connect your PC to a CHIL datalogger using a USB to USB Micro cable (see :numref:`Figure %s <fig_adalogger_receiver>`).

.. _fig_adalogger_receiver:

.. figure:: /_static/adalogger_in_receiver.png

    Adafruit Feather M0 Adalogger USB connection and SD card on CHIL Datalogger PCB.

On a Windows PC, load the Device Manager (`Windows Key + R` then enter `devmgmt.msc`) and identify the *Ports (COM & LPT)* section (:numref:`Figure %s <fig_device_manager>`). If no other serial devices are connected to your PC, then the datalogger port will be the only one shown in the list. You can check that the COM port address is correct by removing the USB cable and verifying that the entry disappears from the device manager list. Reconnect the USB cable when finished.

.. _fig_device_manager: 

.. figure:: /_static/device_manager.png

    Windows Device Manager to identify COM port address (*COM5* in this example).

Starting cryodecoder
^^^^^^^^^^^^^^^^^^^^
.. important:: 
    These instructions assume you have followed the `setup instructions <setup>`__ If you installed cryodecoder to a `virtual environment <https://docs.python.org/3/library/venv.html>`__ then make sure it is activated before continuing.

To launch cryodecoder, open a new terminal (command prompt) window. If necessary, locate and activate the virtual environment where you have installed cryodecoder. 

Cryodecoder saves data to the a folder named ``data`` within the current working directory in the command prompt window. To navigate to a location where you wish to save data, use the ``cd`` command:

.. code-block:: shell

    cd /path/to/my/data

When started, cryodecoder will make a new folder with the current PC timestamp within the ``data`` folder. This means that you can use the same ``data`` folder for multiple sessions using cryodecoder.

To start the cryodecoder software, enter the following command in the terminal window, replacing ``COM5`` with the name of the COM port you identified earlier. This runs cryodecoder in ``serial`` mode and sets ``COM5`` as the port we wish to connect to.

.. hint::
    If you are using one of the Radiocrafts `development kit boards <https://radiocrafts.com/products/development-kits/buy-a-development-kit-from-radiocrafts/>`__, it is possible to decode MBus packets without using a CHIL datalogger by selecting the `-m mbus` option when starting cryodecoder. 

.. code-block:: shell

    cryodecoder -p COM5 serial

Also shown in :numref:`Figure %s <fig_serial_cli_launch>` is the output from cryodecoder help message which explains the various options that can be provide to the receiver. 

.. _fig_serial_cli_launch:

.. figure:: /_static/serial/serial_cli_launch.png

    cryodecoder help menu and command to launch in *serial* mode.

Using the display
^^^^^^^^^^^^^^^^^

If you have connected successfully to the datalogger, you will periodically see messages from the receiver which provide updates on the status of the various on-board sensors (:numref:`Figure %s <fig_serial_cli_receiver_sensors>`). Additionally, information is also provided on whether there are still packets in the buffer which remain to be transmitted over the satellite connection or saved to the SD card. A countdown is also provided until the next time at which the receiver time will be updated using the satellite connection. 

.. _fig_serial_cli_receiver_sensors:

.. figure:: /_static/serial/cli_receiver_sensors.png

    Example output from cryodecoder displaying the datalogger environmental sensor values.

When a packet is received from a CHIL instrument, multiple sources of information are sent to the command line (:numref:`Figure %s <fig_serial_received_packet>`). Some of this originates from the serial debugging output from the datalogger, which is interspersed with the logging output from cryodecoder indicating that a packet has been received. 

.. _fig_serial_received_packet:

.. figure:: /_static/serial/received_packet_annotated.png

    cryodecoder command line output when received a packet from Cryowurst.

Additional output may also appear from the receiver while it is performing operations using the Iridium modem, such as transmitting a packet over the sallite connection (:numref:`Figure %s <fig_serial_transmitting_packet>`).

.. _fig_serial_transmitting_packet:

.. figure:: /_static/serial/cli_transmitting_packet.png

    cryodecoder command line output showing debugging information related to the Iridium modem.