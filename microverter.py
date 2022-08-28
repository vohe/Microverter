#!/usr/bin/env python3

__author__ = "Volker Heggemann"
__copyright__ = "Copyright 2022, Volker Heggemann"
__credits__ = ["The PySimpleGui Project", "other"]
__license__ = "CC BY-NC-SA"
__version__ = "0.1"
__maintainer__ = "vohe"
__email__ = "vohegg@gmail.com"
__status__ = "Alpha Release"

# Imports global libs
import atexit
# for logging to file or stdout this is given.
# uses this instead of print something out to stdout!
import logging
import sys
import time
from datetime import datetime

# What a simple, loveley gui framework
# credits to : https://github.com/PySimpleGUI/PySimpleGUI
import PySimpleGUI as Sg
import requests
import validators
from requests.auth import HTTPBasicAuth

# eventlooptime is used by PySimpleGui for leaving the window-loop
# shorten this if your computer is not busy
# I use 400 on my old thinkpad T430 (2CPU,max. RAM)

eventlooptime = 200
debuglevel = logging.CRITICAL
debug_console = True

if debug_console:
    logging.basicConfig(stream=sys.stdout, level=debuglevel)
else:
    logging.basicConfig(filename="microverter.log", level=debuglevel)

logging.info(f'\n\nStarting microverter {datetime.now()}\n')


# logging.debug('This message should go to the log file')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Öffi')


# This class is used to read the data from the Bosswerk, Deye, e.g. Microinverter.
class BosswerkDeyeMicroinverter:

    def __init__(self, start_url='http://192.168.178.50/status.html',
                 start_timer=10,
                 start_user='',
                 start_username='admin',
                 start_password='admin',
                 start_pricekw='0.41'
                 ):
        atexit.register(self.exit_called)
        self.happened = False
        self.window = Sg.Window('none')
        # Data to proceed
        self.request_url = start_url
        self.request_time = start_timer  # request after xx seconds
        self.request_lasttime = time.time()
        self.isvalid_url = False
        self.user = start_user
        self.username = start_username
        self.password = start_password
        self.logger_serial = ''
        self.wpeaknow = ''
        self.kwtoday = ''
        self.kwtotal = ''
        self.uptime = ''
        self.price_kw = start_pricekw
        self.price_now = 0.0
        self.price_today = 0.0
        self.price_total = 0.0

        self.aboolean = False

    @staticmethod
    def time_convert(sec):
        """
        It takes a number of seconds and returns a tuple of hours, minutes, and seconds

        :param sec: the number of seconds to convert (an integer)
        :return: the hours, minutes, and seconds of the time.
        """

        minutes = sec // 60
        sec = sec % 60
        hours = minutes // 60
        minutes = minutes % 60
        return int(hours), int(minutes), int(sec)

    def timer(self, timer, timeformat='sec'):
        """
        It takes the time elapsed since the timer was started and returns the time in seconds, minutes, or hours

        :param timer: The timer variable is the time that you want to start the timer from
        :param timeformat: 'sec' for seconds, 'min' for minutes, 'hour' for hours, defaults to sec (optional)
        :return: The time in seconds, minutes, or hours.
        """
        h, m, s = 0, 0, 0
        if timer != time.time():
            time_lapsed = time.time() - timer
            h, m, s = self.time_convert(time_lapsed)
        if timeformat == 'sec':
            return s
        if timeformat == 'min':
            return m
        if timeformat == 'hour':
            return h

    def exit_called(self):
        """
        "If the exit_called function has already been called, then return. Otherwise, set the happened variable to True
        and log a message."

        The reason for this is that the atexit() function can call the exit_called function twice. This is a bug in
        Python
        :return: The exit_called function is being returned.
        """
        # do this only one time
        # this is nessesary because the atexit() function could call this twice!!
        if self.happened:
            return
        self.happened = True
        logging.info("Cleaning up...")

    @staticmethod
    def get_webdata(data):
        """
        It takes a string of data, splits it into lines, then finds the lines that contain the word 'webdata' and are
        not in the first 10 characters of the line. It then strips off the 'var' and ';' characters, and splits the
        string into a key and a value. It then adds the key and value to a dictionary

        :param data: the data string from the web page
        :return: A dictionary with the key-value pairs of the webdata.
        """
        data_dict = {}
        for each in data.splitlines():
            # find the lines contain the webdata stringslice
            # but only that with webdata stands in a position under 10th.
            if 10 > each.find('webdata') > 0:
                # strip of the var word in front and the ; sign at the end
                key_value_string = str(each.lstrip('var ').rstrip(';')).replace('"', '')
                # print(key_value_string.split('='))
                data_dict[key_value_string.split('=')[0].strip()] = key_value_string.split('=')[1].strip()
        return data_dict

    def get_inverter_data(self, url):
        """
        It takes a URL, makes a request to that URL, and then parses the response

        :param url: the url of the inverter
        :return: the inverter data.
        """
        res = requests.get(url, auth=HTTPBasicAuth(self.username, self.password), timeout=self.request_time)
        # print(res.headers)
        # print(res.text)
        variables = self.get_webdata(res.text)
        res.close()
        logging.debug(variables)
        # print the result
        self.logger_serial = variables['webdata_sn']
        self.wpeaknow = variables['webdata_now_p']
        self.kwtoday = variables['webdata_today_e']
        self.kwtotal = variables['webdata_total_e']
        self.uptime = variables['webdata_utime']
        self.calc_data()
        return

    def calc_data(self):
        """
        It takes the price per kilowatt hour from the user, and then multiplies it by the number of kilowatts used in
        the current hour, the current day, and the total number of kilowatts used since the program was started
        """
        kwprice = float(str(self.price_kw))
        if self.wpeaknow.isnumeric():
            self.price_now = kwprice * float(self.wpeaknow) / 1000
        if not self.kwtoday == '':
            self.price_today = kwprice * float(str(self.kwtoday))
        if not self.kwtotal =='':
            self.price_total = kwprice * float(str(self.kwtotal))

    def set_statusbar_text(self, newtext):
        """
        If the window exists and the status bar exists, update the status bar with the new text and refresh the window

        :param newtext: The text to be displayed in the status bar
        """
        if self.window:
            if self.window["Status"]:
                self.window["Status"].update(newtext)
                self.window.refresh()

    def display(self):
        """
        It creates a GUI window with three tabs, and then loops forever, waiting for events.

        The first tab is the main tab, and it displays the data from the inverter.

        The second tab is the settings tab, and it allows you to change the URL of the inverter, and the price per kW.

        The third tab is the about tab, and it displays the version number of the program.

        The loop is waiting for events, and when it gets one, it checks to see if it's a button press.

        If it is, it checks to see if it's the "Set" button. If it is, it checks to see if the URL is valid.

        If it is, it saves the URL, and updates the display.

        If it's not, it displays an error message.

        If it's not the "Set" button, it checks
        """
        # make a small window show what's going on
        Sg.theme("DarkAmber")  # "Default", "Default1", "DefaultNoMoreNagging" "SystemDefault", "SystemDefault1",
        # 'SystemDefaultForReal'
        sizex = 800
        sizey = 400

        tab1_layout = [
            [Sg.T('Microverter Data:'), ],
            [Sg.T('Request URL'), Sg.Push(), Sg.T('', key='REQUEST_URL')],
            [Sg.T('Logger #'), Sg.Push(), Sg.T('', key='LOGGER_SN')],
            [Sg.T('Wp now'), Sg.Push(), Sg.T('', key='WP_NOW')],
            [Sg.T('kW today'), Sg.Push(), Sg.T('', key='KW_TODAY')],
            [Sg.T('kW total'), Sg.Push(), Sg.T('', key='KW_TOTAL')],
            [Sg.T('work days'), Sg.Push(), Sg.T('', key='UTIME')],
            [Sg.Canvas(key='figCanvas')],
            [Sg.VPush()],
            [Sg.T('Earn now'), Sg.Push(), Sg.T('', key='E_NOW'),
             Sg.T('today'), Sg.Push(), Sg.T('', key='E_TODAY'),
             Sg.T('total'), Sg.Push(), Sg.T('', key='E_TOTAL'),
             Sg.T('next update in '), Sg.Push(), Sg.T('', key='update_sec')],

        ]
        tab2_layout = [
            [Sg.T('Microverter URL'), Sg.Push(), Sg.InputText(default_text=self.request_url, key='URL'),
             Sg.T('', size=(4, 1), key='VALID')],
            [Sg.T('URL request User'), Sg.Push(), Sg.InputText(default_text=self.username, key='USER'), ],
            [Sg.T('URL request Password'), Sg.Push(), Sg.InputText(default_text=self.password, key='PASSWORD'), ],
            [Sg.VPush()],
            [Sg.T('Price per kW'), Sg.Push(), Sg.InputText(default_text=self.price_kw, key='PRICE_KW'), ],
            # save is optional for save configuration, may use later
            [Sg.Button('Set', key='SET'), Sg.Push(), Sg.Button('Save', key='SAVE')]

        ]
        tab3_layout = [
            [Sg.T('About', key="About")],

        ]

        layout = [
            [Sg.TabGroup([[
                Sg.Tab("Main", tab1_layout, key="tab1"),
                Sg.Tab("Settings", tab2_layout, key="tab2"),
                Sg.Tab("About", tab3_layout, key="tab3")
            ]], size=(sizex, sizey), tooltip="Microverter")
            ],
            [Sg.VPush()],
            [Sg.Push(), Sg.Button('Exit', key='EXIT')],
            [Sg.Text(text="Status:", key="Status", size=(60, 2),
                     auto_size_text=True)]

        ]

        # this shows a window with a title and
        # four textlines to access later
        # below there is an exit button

        self.window = Sg.Window("Microverter", layout, size=(sizex, sizey), resizable=True, finalize=True)
        # a loop till ever collect the button events

        while True:  # Event Loop
            event, values = self.window.read(eventlooptime)
            if event in (None, "Exit", "EXIT"):
                self.exit_called()
                break
            if event in 'SET' and values['URL']:
                self.isvalid_url = validators.url(values['URL'])
                self.request_lasttime = time.time() - self.request_time + 3
                if self.isvalid_url:
                    self.request_url = values['URL']
                    self.window['REQUEST_URL'].update(self.request_url)
                    self.window['VALID'].update('is ok')
                else:
                    self.window['VALID'].update('No ')
            self.password = values['PASSWORD']
            self.user = values['USER']

            looptimer = self.timer(self.request_lasttime, 'sec')
            self.window['update_sec'].update(self.request_time - looptimer + 1)

            if self.timer(self.request_lasttime, 'sec') > self.request_time:
                self.request_lasttime = time.time()
                if self.isvalid_url:
                    self.get_inverter_data(self.request_url)
                    self.calc_data()
                    self.window['LOGGER_SN'].update(self.logger_serial)
                    self.window['WP_NOW'].update(self.wpeaknow)
                    self.window['KW_TODAY'].update(self.kwtoday)
                    self.window['KW_TOTAL'].update(self.kwtotal)
                    self.window['UTIME'].update(self.uptime)
                    self.window['E_NOW'].update(round(self.price_now, 2))
                    self.window['E_TODAY'].update(round(self.price_today))
                    self.window['E_TOTAL'].update(round(self.price_total))

        self.window.close()


def main():
    """
    > The function `main()` creates an instance of the class `BosswerkDeyeMicroinverter` and calls the method
    `display()` on that instance
    """
    inverter = BosswerkDeyeMicroinverter()
    inverter.display()


# Main body
if __name__ == '__main__':
    main()
"""    
    # or call all the function manually ?
    # first connect direct with the micro inverter there is a ssid like AP_Serialnumber
    # WLAN Password for that normally is 12345678
    # then the start_url should be 10.10.100.254
    # there you could connect to access point or adhoc mode
    manual_inverter = BosswerkDeyeMicroinverter(start_url='http://192.168.178.50/status.html')
    if validators.url(manual_inverter.request_url):
        logging.info('URL is valid')
        manual_inverter.get_inverter_data(manual_inverter.request_url)
        manual_inverter.calc_data()
        print(f'Logger serial Number {manual_inverter.logger_serial}')
        print(f'Watt peak now     : {manual_inverter.wpeaknow} W ')
        print(f'and price per kWh : {manual_inverter.price_kw} \n')
        print(f'KiloWatt today    : {manual_inverter.kwtoday} kWh  earned {manual_inverter.price_today} ')
        print(f'KiloWatt total    : {manual_inverter.kwtotal} kWh  earned {manual_inverter.price_total}')
"""
