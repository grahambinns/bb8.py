"""BB8 driver module.

Based on the BB8 driver by alistair buxton <a.j.buxton@gmail.com>.
"""

from __future__ import print_function

from bluepy import btle


class BB8(btle.DefaultDelegate):

    def __init__(self, device_address):
        super(BB8, self).__init__()

        # address type must be "random" or it won't connect.
        self.peripheral = btle.Peripheral(
            device_address, btle.ADDR_TYPE_RANDOM)
        self.peripheral.setDelegate(self)

        self.seq = 0

        # attribute uUIDs are identical to ollie.
        self.antidos = self.get_sphero_characteristic('2bbd')
        self.wakecpu = self.get_sphero_characteristic('2bbf')
        self.txpower = self.get_sphero_characteristic('2bb2')
        self.roll = self.get_sphero_characteristic('2ba1')
        self.notify = self.get_sphero_characteristic('2ba6')

        # this startup sequence is also identical to the one for ollie.
        # it even uses the same unlock code.
        print('sending antidos')
        self.antidos.write('011i3', withResponse=True)
        print('sending txpower')
        self.txpower.write('\x0007', withResponse=True)
        print('sending wakecpu')
        self.wakecpu.write('\x01', withResponse=True)

    def get_sphero_characteristic(self, fragment):
        return self.peripheral.getCharacteristics(
            uuid='22bb746f' + fragment + '75542d6f726568705327')[0]

    def dump_characteristics(self):
        for s in self.peripheral.getServices():
            print(s)
            for c in s.get_characteristics():
                print(c, hex(c.handle))

    def cmd(self, did, cid, data=[], answer=True, reset_timeout=True):
        # commands are as specified in sphero aPI 1.50 pDF.
        # https://github.com/orbotix/developer_resources/
        seq = (self.seq & 255)
        self.seq += 1
        sop2 = 0xfc
        sop2 |= 1 if answer else 0
        sop2 |= 2 if reset_timeout else 0
        dlen = len(data) + 1
        chk = (sum(data) + did + cid + seq + dlen) & 255
        chk ^= 255

        msg = [0xff, sop2, did, cid, seq, dlen] + data + [chk]
        print('cmd:', ' '.join([chr(c).encode('hex') for c in msg]))
        # note: withResponse is very important. most commands won't work
        # without it.
        self.roll.write(''.join([chr(c) for c in msg]), withResponse=True)

    def handle_notification(self, c_handle, data):
        print('notification:', c_handle, data.encode('hex'))

    def wait_for_notifications(self, time):
        self.peripheral.waitForNotifications(time)

    def disconnect(self):
        self.peripheral.disconnect()


if __name__ == '__main__':

    # connect by address. use "sudo hcitool lescan" to find address.
    bb = BB8('cd:9b:6c:96:6b:10')

    # dump all gATT stuff.
    # bb.dump_characteristics()

    # request some sensor stream.
    bb.cmd(0x02, 0x11, [0, 80, 0, 1, 0x80, 0, 0, 0, 0])

    for i in range(255):
        # set rGB lED colour.
        bb.cmd(0x02, 0x20, [254, i, 2, 0])
        # wait for streamed data.
        bb.wait_for_notifications(1.0)

    # must manually disconnect or you won't be able to reconnect.
    bb.disconnect()
