#!/usr/bin/env python
# encoding: utf-8

import os
import signal
import random
import glib
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk
from gi.repository import AppIndicator3
from gi.repository import Notify
from gi.repository import GObject
from datetime import datetime
import csv
import urllib2

TAKE_LAST_ROW = 'take_last_row'

class WidgetState:
    def __init__(self, threashold, icon=None, notification=None):
        self.threashold = threashold
        self.icon = icon
        self.notification = notification
    

class SpreadsheetWidget:

    def __init__(self):

        self.APPINDICATOR_ID = 'spreadsheet_widget'

        ### RELEVANT CONSTANTS ###
        # Longest possible pattern so that widget does not jump around when data changes
        self.label_guide = "9999.99 of 9999.99€"
        # Output template, multiple strings possible
        self.label_template = "%s of %s€"
        # Spreadsheet dats url
        self.data_url = "https://docs.google.com/spreadsheets/d/1RYI2d9Wt6jT781cL_yiJTkrAbZ1NSPf-eEWoDpGv7I4/gviz/tq?tqx=out:csv&sheet=SavingsProgress"
        # Icon
        self.icon_path = os.path.abspath('assets/dot-arrow-white.svg')
        # Update frequency in miliseconds
        self.update_frequency = 10*60*1000
        # Data feed or file row to look for, can use integer or TAKE_LAST_ROW
        self.data_row = 1
        # Data feed or file columns to look for
        self.data_columns = [2,5]
        # Define widget states. 
        # Threasholds will be checked against first value of the processed row
        # If exeeded, appropriate state icon will be set and notification shown
        self.states = []
        self.states.append(
            WidgetState(
                threashold = 0,
                icon = os.path.abspath('assets/dot-arrow-white.svg')))
        self.states.append(
            WidgetState(
                threashold = 500, 
                icon = os.path.abspath('assets/dot-arrow-yellow.svg')))
        self.states.append(
            WidgetState(
                threashold = 800, 
                icon = os.path.abspath('assets/dot-arrow-red.svg'),
                notification = {
                    'title': "<b>Alert</b>", 
                    'message': "This is a message",
                    'icon': None 
                }))
        # Notification cooldown - a minimal time in seconds between subsequent notifications. 'None' to have no limit
        self.notification_cooldown = 60 * 60 # 1 hour
        # Show random testing data?
        self.show_random_data_for_testing = True
        ### END CONSTANTS ###

        self.indicator = AppIndicator3.Indicator.new(self.APPINDICATOR_ID, self.icon_path, AppIndicator3.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_property('label-guide', self.label_guide)
        self.indicator.set_menu(self.build_menu())

        Notify.init(self.APPINDICATOR_ID)
        self.last_notification_time = datetime.min

        self.update_label();


    def build_menu(self):
        menu = Gtk.Menu()

        item_update = Gtk.MenuItem('Update')
        item_update.connect('activate', self.update_label)
        menu.append(item_update)

        ### Uncoment to have 'Quit' as an item in widget menu
        # item_quit = Gtk.MenuItem('Quit')
        # item_quit.connect('activate', self.quit)
        # menu.append(item_quit)

        menu.show_all()
        return menu


    def format_label(self, data):
        return self.label_template % data


    def show_notification(self, notification):
        if self.notification_cooldown is None:
            return

        last_notification_age = datetime.now() - self.last_notification_time

        if last_notification_age.total_seconds() > self.notification_cooldown:
            Notify.Notification.new(
                notification['title'],
                notification['message'],
                notification['icon']).show()
            self.last_notification_time = datetime.now()


    def update_state(self, row):
        state_to_set = None
        for state in self.states:
            if row[0] > state.threashold:
                state_to_set = state

        if state_to_set:
            if state_to_set.icon:
                GObject.idle_add(
                    self.indicator.set_icon, 
                    state_to_set.icon,
                    priority=GObject.PRIORITY_DEFAULT)

            if state_to_set.notification:
                self.show_notification(state_to_set.notification)
                

    def process_row(self, row):
        current_column = 1
        result = []
        for item in row:
            if current_column in self.data_columns:
                if self.show_random_data_for_testing:
                    result.append(round(random.uniform(1,1200), 2))
                else:
                    result.append(item)
            current_column += 1 

        self.update_state(result)
        return result    


    def get_data(self):
        response = urllib2.urlopen(self.data_url)
        data = csv.reader(response)

        current_row = 1
        for data_row in data:
            if current_row == self.data_row:
                result = self.process_row(data_row)
                break
            current_row += 1

        if self.data_row == TAKE_LAST_ROW:
            # this will process last row as it will be in the variable
            result = self.process_row(data_row)
 
        return tuple(result)


    def update_label(self, widget=None):
        label = self.format_label(self.get_data())
        self.indicator.set_label(label, self.label_guide)

        glib.timeout_add(self.update_frequency, self.update_label)


    def quit(self, widget=None):
        Notify.uninit()
        Gtk.main_quit()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    widget = SpreadsheetWidget()
    Gtk.main()