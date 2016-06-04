#!/usr/bin/python

import sys
import time
import tables

sys.path.append('../py-korad-serial')
from koradserial import KoradSerial

############# CONSTANCE
DEVSERIAL = '/dev/ttyUSB0'
SAVEDAYS = '365'
DATASTORE = 'battery_charger.hdf5'
HOUR_TO_SEC = 60*60

############# CLASSES
class LoadRow(tables.IsDescription):
    time = tables.Float64Col()
    voltage = tables.Float64Col()
    current = tables.Float64Col()

class battery_charger(object):
    def __init__(self, voltage=1.0, current=0.1, maxtime=2.0):
        self.voltage = voltage
        self.current = current
        self.maxtime = maxtime
        self.h5 = tables.openFile(DATASTORE,'a')
        
    def load(self):
        h5path = time.strftime('/Date_%Y-%m-%d/Time_%H_%M_%S').split('/')
        if '/'+h5path[1] not in self.h5:
            h5group = self.h5.createGroup('/',h5path[1])
        h5group = self.h5.createGroup('/'+h5path[1], h5path[2])
        h5table = self.h5.createTable(h5group, 'load', LoadRow)
        
        
        ps = KoradSerial(DEVSERIAL)
        ps.output.off()
        ps.beep.off()
        ch1 = ps.channels[0]
        ch1.current = self.current
        ch1.voltage = self.voltage
        ps.output.on()

        starttime = time.time()

        currenttime = time.time()
        while (currenttime-starttime) < self.maxtime*HOUR_TO_SEC:
            time.sleep(5)
            currenttime = time.time()
            voltage = ch1.output_voltage
            current = ch1.output_current
            print time.ctime(currenttime), 'V: ', voltage, '  I: ', current
            row = h5table.row
            row['time'] = currenttime
            row['voltage'] = voltage
            row['current'] = current
            row.append()
        h5table.flush()

        ps.output.off()



############ FUNCTIONS
def help():
    print 'usage: ' + __name__ + 'cmd [parameters]'
    print 'commands and parameters:'
    print '  load voltage current maxtime: loads a battery'
    print '  show [dataset]: displays the load graphs of the last load'
    

############# MAIN
if __name__ == '__main__':
    bc = battery_charger(1.45,.5,4.0)
    bc.load()
    sys.exit()
    
    if len(sys.argv) < 2:
        help()
        sys.exit()

    cmd = sys.argv[1]
    if cmd == 'load':
        pass
    elif cmd == 'show':
        pass
