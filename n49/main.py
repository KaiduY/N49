"""
This code has been written for the Astro Pi Mission Space Lab 2021-2022 by the team N49.
The main goal of this code is to analyze Earth's magnetic field and record the data to be further processed.
"""

from datetime import time, datetime, timezone
from orbit import ISS
from logzero import logger, logfile
from gpiozero import CPUTemperature
from sense_hat import SenseHat
from pathlib import Path
import csv
import numpy as np
import os
import time


# Header for the CSV files
Header = ('time', 'temperature', 'cpu_temp', 'magnet_x', 'magnet_y', 'magnet_z', 'gyro_pitch', 'gyro_roll', 'gyro_yaw', 
          'accel_pitch', 'accel_roll', 'accel_yaw', 'gyro_x', 'gyro_y', 'gyro_z', 'accel_x', 'accel_y', 'accel_z', 'lat', 'long', 'elev')


def gatherData():
    """
    Registers data measurements and writes data to the file.
    """
    # Execut the function only if the delay has passed.
    if(gatherData_timer.ready()):

        # Read sensors data and compute ISS possition.
        location = ISS.coordinates()
        magnet = sense.get_compass_raw()
        gyro_o = sense.get_gyroscope()
        accel_o = sense.get_accelerometer()
        gyro_raw = sense.get_gyroscope_raw()
        accel_raw = sense.get_accelerometer_raw()
        
        # Format data in a single line according to the CSV header.
        line = (time.time_ns(), sense.temperature, CPUTemperature().temperature, magnet['x'], magnet['y'], magnet['z'], gyro_o['pitch'], gyro_o['roll'], gyro_o['yaw'],
                accel_o['pitch'], accel_o['roll'], accel_o['yaw'], gyro_raw['x'], gyro_raw['y'], gyro_raw['z'], accel_raw['x'], accel_raw['y'], accel_raw['z'], location.latitude.degrees, location.longitude.degrees, location.elevation.km)

        # Puts everything into a buffer in order not to write to the file every time.
        data_buffer.append(line)

        # Writes the data when the buffer's length is 10.
        if len(data_buffer) > 10:
            data.writeBuffer(data_buffer)
            data_buffer.clear()


def updateDisplay():
    """
    Updates the LED matrix LED by LED.
    """
    # Updates the LED only if the delay has passed.
    if(updateDisplay_timer.ready()):

        # Makes a refrence to the 2 global variables storing current LED possition.
        global LED_x
        global LED_y

        # Clear the matrix and turn the LED on with randomized color.
        sense.clear()
        sense.set_pixel(LED_x, LED_y, np.random.randint(255, size=(3)))

        # Goes to the next position.
        LED_x = LED_x + 1

        # If it reaches the end of a line it goes to the next one.
        if LED_x > 7:
            LED_x = 0
            LED_y = LED_y + 1

        # If it reaches the end of the matrix it returns to the start.
        if LED_y > 7:
            LED_y = 0


class file:
    """
    A class used to interact with CSV files.

    ...

    Attributes
    ----------
    filename (str): name of the file to be written, must end in "0.csv".
    header (list): the header used when creating the CSV files.
    path (str): the path to the current working directory or the directory where the file should be saved.

    Methods
    -------
    write(data)
    writeBuffer(data): Writes multiple lines at once to the file.
    """
    def __init__(self, filename, header, path):
        """
        The constructor for the file object.

        Parameters
        ----------
        filename (str): name of the file to be written, must end in "0.csv".
        header (list): the header used when creating the CSV files.
        path (str): path to the current working directory or the directory where the file should be saved.

        """
        self.filename = filename
        self.header = header
        self.isCreated = False  # A flag used to tell if the file exists.
        self.passLimit = False  # A flag used to limit the number of files created.
        self.index = 0  # The index of the currently used file.
        self.maxCount = 5  # How many files can be created.
        self.maxSize = 30 * 1024 * 1024  # Maximum file size in bytes, 30 * 1024 * 1024 = 30 MB.
        self.parent_path = path

    def write(self, data):
        """
        Writes a single line to the file.

        Parameters
        -------
        data (list): data to be written, should respect the preset header.
        """

        # Only writes if the size and the number of files is not exceed.
        self.fileSystemHandler()
        if not self.passLimit:
            with open(self.parent_path + self.filename, 'a', buffering=1) as f:
                writer = csv.writer(f)
                writer.writerow(data)

    def writeBuffer(self, data):
        """
        Writes multiple lines to the file.

        Parameters
        -------
        data (list): data to be written, should respect the preset header.
        """

        # Only writes if the size and the number of files is not exceed.
        self.fileSystemHandler()
        if not self.passLimit:
            with open(self.parent_path + self.filename, 'a', buffering=1) as f:
                writer = csv.writer(f)
                writer.writerows(data)

    def create(self):
        """
        Internal function used to create a new file.
        """
        with open(self.parent_path + self.filename, 'w', buffering=1) as f:
            writer = csv.writer(f)
            writer.writerow(self.header)  # Write the header of the CSV file.
            self.isCreated = True  # Flag that the file is created.

    def sizeCheck(self):
        """
        Internal function used to limit the size of a file.

        Returns
        -------
        True if the size of the file exceeds the preset limit, False otherwise.
        """
        currentSize = os.path.getsize(self.parent_path + self.filename)
        return currentSize > self.maxSize

    def fileSystemHandler(self):
        """
        Internal function used to handle creating files.
        """
        # Only creates a new file if the limit isn't achieved.
        if not self.passLimit:

            if not self.isCreated:
                self.create()

            # Go to a new file only if the maximum size is achieved with the current one.
            if self.sizeCheck() and self.index < self.maxCount:
                # Modify the filename so the file will not be overwritten (e.g. data0.csv --> data1.csv).
                new_filename = self.filename.replace(
                    str(self.index), str(self.index+1))
                self.filename = new_filename

                # Increase the index and flag that the file is not yet created.
                self.index = self.index + 1
                self.isCreated = False

            # Flag if the limit is achieved.
            if self.index == self.maxCount:
                self.passLimit = True


class delayHandeler:
    """
    A class to handle delay between functions.

    ...

    Attributes
    ----------
    interval (int): the delay between functions.

    Methods
    -------
    ready(): check if the delay is finished.
    getInterval(): return the current interval value.
    setInterval(newInterval): change the current interval value.
    getDelta(): return the time left until the delay is finished.
    """

    def __init__(self, interval):
        """
        The constructor for the delayHandeler object.

        Parameters
        ----------
        interval (int): the delay between functions.
        """
        self.intv = interval
        self.lastTime = self.currrentTime()

    def currrentTime(self):
        """
        Return the system time in milliseconds.

        Returns
        -------
        now (int): Time in milliseonds. 
        """
        now = time.time() * 1000
        return now

    def ready(self):
        """
        Primary function of the object.
        Used to check if it is the time to execute a specific task according to the interval value.

        Returns
        -------
        True if enough time has passed since the last call, False otherwise.
        """
        current_time = self.currrentTime()
        if current_time - self.lastTime > self.intv:
            self.lastTime = current_time  # Reseting lastTime allows this function to be called again (e.g. in a loop).
            return True
        return False

    def getInterval(self):
        """
        Returns the interval value.

        Returns
        -------
        intv (int)
        """
        return self.intv

    def setInterval(self, newInterval):
        """
        Set the interval value.

        Parameters
        -------
        newInterval (int)
        """
        self.intv = newInterval

    def getDelta(self):
        """
        Returns the time left in milliseconds until the delay is finished.

        Returns
        -------
        dt (int)
        """
        dt = self.intv + self.lastTime - self.currrentTime()
        return dt


LED_x = 0 
LED_y = 0
data_buffer = []

# A second is 1000 milliseconds and so on.
second = 1000 
minute = 60 * second
hour = 60 * minute

sense = SenseHat()

# Initialize the timers with the required delay.
main_timer = delayHandeler(3*hour - 2*minute)
gatherData_timer = delayHandeler(100)
updateDisplay_timer = delayHandeler(10 * second)

# The path to the current directory in a string format.
dir_path = str(Path(__file__).parent.resolve()) + "/"

logfile(dir_path + "logger.log")
data = file('output0.csv', Header, dir_path)

logger.info('Start! '+ str(datetime.now(timezone.utc)))

# Runs the code until main_timer (almost 3 hours) is done.
while not main_timer.ready():

    try:
        gatherData()
        updateDisplay()

    except Exception as e:
        logger.error('{}: {})'.format(e.__class__.__name__, e))

# Clear the LED matrix after the experiment is finished
sense.clear()

logger.info('Done! '+ str(datetime.now(timezone.utc)))
