import logging
import socket
import channelsimulator
import utils
import sys
import math
import random

class Sender(object):

    def __init__(self, inbound_port=50006, outbound_port=50005, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.sndr_setup(timeout)
        self.simulator.rcvr_setup(timeout)

    def send(self, data):
        raise NotImplementedError("The base API class has no implementation. Please override and add your own.")


class BogoSender(Sender):

    def __init__(self):
        super(BogoSender, self).__init__()

    def send(self, data):
        self.logger.info("Sending on port: {} and waiting for ACK on port: {}".format(self.outbound_port, self.inbound_port))
        while True:
            try:
                self.simulator.u_send(data)  # send data
                ack = self.simulator.u_receive()  # receive ACK
                self.logger.info("Got ACK from socket: {}".format(
                    ack.decode('ascii')))  # note that ASCII will only decode bytes in the xrange 0-127
                break
            except socket.timeout:
                pass


#######################################################
class MySender(Sender):
    #initial data setup
    Data = SegNo = Block = BlockStart =  0				#In order: data, segment number, block,number, and block beginning
    BlockEnd = MaxBlock = 255                                                 # largest block size
    buffer_BlockEnd = buffer_start = SequenceNo = 0							# buffer beginning and end as well as sequence number declared
    SentCopies = SentFlag = ResentFlag = 0											# Tracks number of times a packet is re/sent,flags of whether is has been sent, and of whther it was resent
    def __init__(self, DATA, timeout = 0.5):
        super(MySender, self).__init__()
        self.Data = DATA
        self.timeout = timeout
        self.simulator.sndr_socket.settimeout(self.timeout)
        DataLength = len(self.Data)
        self.SegNo = int(math.ceil(DataLength/float(self.MaxBlock)))

    def send(self, data):			# Send Function
        for s in self.splitBlock(self.Data, self.MaxBlock, self.Block):
            try:
                if self.ResentFlag==0:									# Firstatempt at data transfer
                    seg = MyBlock(SequenceNo = 0, AckNo = 0, CheckSum = 0, data = s)
                    seg.SequenceNo = MyBlock.SeqNum(self, self.SequenceNo, self.MaxBlock)
                    self.SequenceNo = seg.SequenceNo
                    SendArray = bytearray([seg.CheckSum, seg.AckNo, seg.SequenceNo])		# Create Data array to be sent to receiver
                    SendArray = SendArray + s
                    seg.CheckSum = MyBlock.CheckSum(self, SendArray)						# Makes checksum section for the data
                    SendArray[0] = seg.CheckSum
                    self.simulator.u_send(SendArray)

                while 1:			# Processing data from receiver
                    RCVRArray = self.simulator.u_receive()
                    CheckVal = ~RCVRArray[0]        # Invert the bits in the checksum row
                    for i in xrange(1, len(RCVRArray)):
                    	CheckVal = CheckVal ^ RCVRArray[i]    # XOR data
                    	if CheckVal == -1:
							if RCVRArray[1] == self.SequenceNo:
								CorruptAck = 1                 # If there is a bit that is not a 1, (meaning the number as a signed int cannot be -1) then there was a problem
							elif RCVRArray[1] == (self.SequenceNo + len(s)) % 256:
								CorruptAck = 2
							else:
								CorruptAck = 3
                    	else:
                    		CorruptAck = 0

                    if CorruptAck==1:				#Case in which sequence number is right
                        self.SentFlag = 1
                        self.simulator.u_send(SendArray)
                    if CorruptAck==2:                        # An Ack of a higher number means that the one we are concerned with got through
                        self.SentCopies = 0
                        if self.timeout > 0.5:
                            self.timeout =self.timeout - 0.5
                        self.simulator.sndr_socket.settimeout(self.timeout)
                        self.ResentFlag = 0
                        break
                    if CorruptAck==3:# Error, so resend data
                            self.simulator.u_send(SendArray)
                    else:
                        resendData(SendArray, self)			# If Ack was corrupted,resend that data and wait, limit time to wait if 3 attempts have been made

            except socket.timeout:							# If timed out,resend that data and wait, limit time to wait if 3 attempts have been made
                self.ResentFlag = 1
                resendData(SendArray, self)

    def splitBlock(self, data, MaxBlock, Block):		#breakup block into smaller blocks
        for i in xrange(self.SegNo):
            Block = Block + 1
            yield data[self.BlockStart:self.BlockEnd]
            self.BlockStart +=  MaxBlock           # These 2 lines update what subblock isnext to be focused on
            self.BlockEnd +=  MaxBlock

def resendData(Array, self):								#Checks if the received ACK's check sum was compromised or not
		self.simulator.u_send(Array)
		self.SentCopies = self.SentCopies + 1
		if self.SentCopies == 3 and self.SentFlag:
			self.timeout = self.timeout+1
			self.simulator.sndr_socket.settimeout(self.timeout)
			self.SentCopies = 0
			if self.timeout > 5:
				print("Timed out")
				exit()

class MyBlock(object):									# Data block with error checking

    def __init__(self, CheckSum, SequenceNo, AckNo, data = []):
        self.CheckSum = 0
        self.AckNo = 0
        self.SequenceNo = 0
        self.data = data

    @staticmethod
    def SeqNum(self, PrevSeqNo, MaxBlock):
        val = PrevSeqNo + MaxBlock
        val = val % 256
        return val

    @staticmethod
    def CheckSum(self, data):										# casts data and XOR's to do check sum
        DataByteArray = bytearray(data)
        LengthData = len(bytearray(data))
        CheckVal = 0
        for i in xrange(LengthData):
            CheckVal =CheckVal ^ DataByteArray[i]
        return CheckVal


if __name__ == "__main__":
    sndr = MySender( bytearray(sys.stdin.read()))			# tests out and sends bogosender
sndr.send( bytearray(sys.stdin.read()))
