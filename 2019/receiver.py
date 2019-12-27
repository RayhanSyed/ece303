import logging
import channelsimulator
import utils
import sys
import socket

class Receiver(object):

    def __init__(self, inbound_port=50005, outbound_port=50006, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.rcvr_setup(timeout)
        self.simulator.sndr_setup(timeout)

    def receive(self):
        raise NotImplementedError("The base API class has no implementation. Please override and add your own.")


class BogoReceiver(Receiver):
    ACK_DATA = bytes(123)

    def __init__(self):
        super(BogoReceiver, self).__init__()

    def receive(self):
        self.logger.info("Receiving on port: {} and replying with ACK on port: {}".format(self.inbound_port, self.outbound_port))
        while 1:
            try:
                 data = self.simulator.u_receive()  # receive data
                 self.logger.info("Got data from socket: {}".format(
                     data.decode('ascii')))  # note that ASCII will only decode bytes in the xrange 0-127
	         sys.stdout.write(data)
                 self.simulator.u_send(BogoReceiver.ACK_DATA)  # send ACK
            except socket.timeout:
                sys.exit()

##############################################3
class MyReceiver(Receiver):
    LastAckNo, ResentFlag, SentCopies = -1, 0, 0
    RCVRArray = bytearray([0,0,0,0])
    MostRecentAck = bytearray([0,0,0])

    def __init__(self, timeout = 0.5):
        super(MyReceiver, self).__init__()
        self.timeout = timeout
        self.simulator.rcvr_socket.settimeout(self.timeout)

    def receive(self):
        while 1:                                      # Waiting for data
            try:
                self.RCVRArray = self.simulator.u_receive()
                if self.timeout > 0.5:          # Receive data and check the timeout
                    self.timeout = self.timeout - 0.5
                    self.SentCopies = 0
                self.send()                     # Send Ack to sender

            except socket.timeout:              # If timeout, resend the most recently made Ack
                self.ResentFlag = 1
                self.simulator.u_send(self.MostRecentAck)
                self.SentCopies =self.SentCopies + 1
                if self.SentCopies >= 3:
                    self.SentCopies = 0
                    self.timeout = self.timeout + 1
                    self.simulator.rcvr_socket.settimeout(self.timeout)
                    if self.timeout > 5:
                        exit()

    def send(self):                             # Make an ack to let sender know what we have received up to
        AckSegment = MySegment()
        AckSuccess = AckSegment.ack(self.RCVRArray, self.LastAckNo)
        if AckSuccess:
            self.LastAckNo = AckSegment.AckNo
        if AckSegment.AckNo < 0:
            AckSegment.AckNo = 0 # we set it to 0 here, it may be set back to -1
        AckSegment.CheckSum = AckSegment.checkSum()
        RCVRArray = bytearray([AckSegment.CheckSum, AckSegment.AckNo])
        MostRecentAck = RCVRArray
        self.simulator.u_send(RCVRArray)

class MySegment(object):

    def __init__(self, CheckSum = 0, SequenceNo = 0, AckNo = 0, data = []):
        self.CheckSum = CheckSum
        self.SequenceNo = SequenceNo
        self.AckNo = AckNo
        self.data = data

    def checkSum(self):         # Since the receiver segment only has an ACK number, its checksum will just be itself
        return self.AckNo

    def ack(self, data, LastAckNo):     # Checks if  the ACK is valid
        CheckVal =~ data[0]            # Invert the bits in the checksum row
        for i in xrange(1,len(data)):
            CheckVal = CheckVal ^ data[i]        # XOR data
        if CheckVal == -1:
            AckSuccess = 1                     # If there is a bit that is not a 1, (meaning the number as a signed int cannot be -1) then there was a problem
        else:
            AckSuccess = 0
        if AckSuccess:
            self.AckNo = (data[2] + len(data[3:])) % 256
            if data[2] == LastAckNo or LastAckNo == -1:
                sys.stdout.write("{}".format(data[3:]))
                sys.stdout.flush()
                return 1
        else:
            pass
        return 0

if __name__ == "__main__":
    rcvr = MyReceiver()                                 # test out and sends  BogoReceiver
rcvr.receive()
