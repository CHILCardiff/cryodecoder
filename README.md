# Cryodecoder
Decoding raw data CHIL instruments and dataloggers.

## Quickstart
To use `cryodecoder` from the command line, you will need to have Python 3.13 or later which can be downloaded from [here](https://www.python.org/downloads/release/python-3146/).

> [!NOTE]
> It is advised to select the option which adds Python to the PATH variable so you can use it directly from a command line instance.

Once you have installed Python, you can install cryodecoder by entering the commands below in the command line:

```bash
python -m pip install git+https://github.com/chilcardiff/cryodecoder.git
```
Once the installation is complete, run the command below to start `cryodecoder` in serial (monitoring) mode

```bash
cryodecoder serial --port COM11
```

replacing `COM11` with the port corresponding to a connected CHIL receiver or [RadioCrafts MBus modem](https://radiocrafts.com/products/development-kits/buy-a-development-kit-from-radiocrafts/). On Windows, you can identify this under "Ports (COM & LPT)" in the "Device Manager" utility. To exit the program in `serial` mode, press `CTRL+C`, this might take a moment or two!

If you have a file from the datalogger (i.e. `chillog.log`), this can be decoded into a CSV file using the command below:

```bash
cryodecoder file --input /path/to/chillog.log --output /path/to/output.csv
```

## Installing from source

```bash
cd /path/to/install/folder
git clone https://github.com/chilcardiff/cryodecoder
```

Alternatively, download the ZIP archive (`<> Code` > `Download ZIP`) from the [GitHub page](https://github.com/chilcardiff/cryodecoder) and extract it to your install location.

Once it is downloaded and extracted, open a command line terminal (i.e. 'cmd' or 'PowerShell') and naviate to the folder where you downloaded `cryodecoder`.

```bash
cd /path/to/install/folder/cryodecoder
```

Create a Python virtual environment using the command below

```bash
python -m venv .env
```

**For the next step, you will need to be connected to the internet.** Activate the virtual environment (using the command below on a Windows machine):

```bash
.env\Scripts\activate
```

And install cryodecoder using the following command:

```bash
python -m pip install -e .
```

Once this has completed, you should succesfully be able to run `cryodecoder` from within the virtual environment.