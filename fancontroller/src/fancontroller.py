#!/usr/bin/python

import time, os
import RPi.GPIO as GPIO
import tables
import numpy

GPIO.setmode(GPIO.BCM)

########## CONSTANTS
BASEDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')
DATADIR = os.path.join(BASEDIR, 'data')
INTERVAL = 60

########## CLASSES

class HDF_Particle(tables.IsDescription):
    timestamp = tables.Float64Col()
    temp_inside = tables.Float32Col()
    temp_outside1 = tables.Float32Col()
    temp_outside2 = tables.Float32Col()
    fanstatus = tables.UInt8Col()

class HDF_Store(object):
    def __init__(self, filename):
        self.filename = filename
        self.hdffile = tables.openFile(self.filename, mode='a')
        self.current_table = None

    def get_table(self):
        if self.current_table:
            self.current_table.flush()
        if '/fan' not in self.hdffile:
            group = self.hdffile.createGroup('/','fan')
        group = self.hdffile.root.fan
        date = time.strftime('D%Y%m%d')
        if date not in group:
            self.current_table = self.hdffile.createTable(group, date, HDF_Particle)
        else:
            self.current_table = eval('group.'+date)
        
    def add_data(self, data=[], timestamp=None):
        date = time.strftime('D%Y-%m-%d')
        if date != self.current_table:
            self.get_table()
        if not timestamp:
            timestamp = time.time()
        particle = self.current_table.row
        particle['timestamp'] = timestamp
        particle['temp_inside'] = data[0]
        particle['temp_outside1'] = data[1]
        particle['temp_outside2'] = data[2]
        particle['fanstatus'] = data[3]
        particle.append()

class Output(object):
    def __init__(self, gpio, inverted=False):
        self.inverted = inverted
        self.gpio = gpio
        self.status = 0

        GPIO.setup(self.gpio,GPIO.OUT)

    def on(self):
        self.status = 1
        if self.inverted:
            GPIO.output(self.gpio, GPIO.LOW)            
        else:
            GPIO.output(self.gpio, GPIO.HIGH)
            

    def off(self):
        self.status = 0
        if self.inverted:
            GPIO.output(self.gpio, GPIO.HIGH)
        else:
            GPIO.output(self.gpio, GPIO.LOW)


class Input(object):
    def __init__(self, gpio, inverted=False):
        self.inverted = inverted
        self.gpio = gpio
        self.status = 0

        GPIO.setup(self.gpio, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def read(self):
        in_ = GPIO.input(self.gpio)
        return in_                
                   
        
class BSP742(object):
    """
    Controll object for Infineon highside switch BSP742
    """
    def __init__(self, gpio_in, gpio_st):
        self.gpio_in = gpio_in
        self.gpio_st = gpio_st
        GPIO.setup(self.gpio_in,GPIO.OUT)
        GPIO.setup(self.gpio_st,GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.status = 0
        self.status_st = 0
        self.off()

    def on(self):
        # read open load status
        
        # turn it on
        self.status = 1
        GPIO.output(self.gpio_in, GPIO.HIGH)
        

    def off(self):
        self.status = 0
        # turn it of
        GPIO.output(self.gpio_in, GPIO.LOW)

    def read(self):
        return GPIO.input(self.gpio_st)
        
class DS20S80(object):
    def __init__(self, device_id):
        self.device_id = str(device_id)

    def read(self):
        try:
            file = open('/sys/bus/w1/devices/' + self.device_id + '/w1_slave')
            filecontent = file.read()
            file.close()
        except:
            return -1.11

        # read temperature and convert to float
        stringvalue = filecontent.split("\n")[1].split(" ")[9]
        temperature = float(stringvalue[2:]) / 1000

        return temperature
       

class Fancontroller(object):
    def __init__(self):
        self.fans = []
        self.setup()

    def setup(self):
        """
        setup all peripherals
        """
        self.led = Output(18)
        self.key = Input(15)
        self.fans.append(BSP742(2,3))
        self.fans.append(BSP742(17,27))
        self.fans.append(BSP742(22,10))
        self.fans.append(BSP742(24,23))
        self.temp_inside = DS20S80('10-000802e74de0')
        self.temp_outside1 = DS20S80('10-000802d791f6')
        self.temp_outside2 = DS20S80('28-031501f534ff')
        self.hdf = HDF_Store(os.path.join(DATADIR, 'fancontroller.h5'))

    def test(self):
        print '\nLED test'
        self.led.on()
        print self.led.status
        time.sleep(1)
        self.led.off()
        print self.led.status
        time.sleep(1)
        print '\nfan test'
        for i, fan in enumerate(self.fans):
            fan.on()
            time.sleep(1)
            fan.off()
            time.sleep(1)
            print 'Fan', i, fan.read()

        print '\ntemp sensor test'
        print 'temp_outside', self.temp_outside1.device_id + u': %6.2f C' % self.temp_outside1.read()
        print 'temp_inside', self.temp_inside.device_id + u': %6.2f C' % self.temp_inside.read()

        print '\nkey test:'
        for i in xrange(10):
            print i, self.key.read()
            time.sleep(1)

    def run(self):
        timeintervals = [(4.0,6.0),
                         (18.0, 21.0)]
        while True:
            time.sleep(INTERVAL)

            run = False
            hr = int(time.time()) % (24*60*60) /(60*60.)
            for start, stop in timeintervals:
                if start < hr and stop > hr:
                    run = True
            if run and not self.fans[1].status:
                for f in self.fans:
                    f.on()
                    time.sleep(2)
            if not run and self.fans[1].status:
                for f in self.fans:
                    f.off()
                    time.sleep(2)

            data = [self.temp_inside.read(),
                    self.temp_outside1.read(),
                    self.temp_outside2.read(),
                    self.fans[0].status]
            print data, hr
            self.hdf.add_data(data)


###### MAIN
fc = Fancontroller()
#fc.test()
fc.run()
