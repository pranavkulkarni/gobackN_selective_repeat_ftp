from socket import *
import sys
import random
import time
from struct import *

def calc_checksum(calc_cs):
	#func to calculate the checksum of the packet
	#calc_cs = pack('IH'+str(len(data))+'s', seq_num, header_last_part, data)

	if len(calc_cs) % 2 != 0:
		calc_cs = calc_cs + str(0)

	it = 0
	check_sum = 0
	while it < len(calc_cs):
		part1 = ord(calc_cs[it])*256 + ord(calc_cs[it+1])
		part2 = 65535 - part1
		part3 = check_sum + part2
		check_sum = (part3 % 65536) + (part3 / 65536)
		it = it + 2

	return (65535 - check_sum)


def checksum(recvdCheckSum, seq_num, header_last_part, data):
	# build a struct packet for check sum calculation as it is easy
	calc_cs = pack('IH'+str(len(data))+'s', seq_num, header_last_part, data)
	if calc_checksum(calc_cs) == recvdCheckSum:
		return True
	else:
		return False


def write(content):
	result = open(filename, 'a')
	result.write(content)
	result.close()


def ack(sequenceNo, clientAddress):
	all_zeroes = int('0000000000000000', 2)
	header_last_part = int('1010101010101010', 2)
	# chr(int('10101010', 2)) + chr(int('10101010', 2))
	send_pkt = pack('IHH', sequenceNo, all_zeroes, header_last_part)
	serverSocket.sendto(send_pkt, clientAddress)


#############
# Main code #
#############

args = sys.argv
if len(args) != 5 and len(args) != 6:
	print "Please input the parameters <port number | filename | p | GBN/SR | N>"
	sys.exit()


file_content = ""
serverPort = int(args[1])
filename = args[2]
p = float(args[3])
protocol = args[4]
N = 0
if protocol == "SR":
	N = int(args[5])

serverSocket = socket(AF_INET, SOCK_DGRAM)
serverIPAddress = gethostbyname(gethostname())
serverSocket.bind(('', serverPort))
last_recvd = -1
seq = 0

received = [] #int buffer to indicate if packet has been received
recv_buffer = [] #buffer to store the received packets
first_in_window = 0
last_in_window = first_in_window + N - 1

for i in range(N):
	received.append(0)
	recv_buffer.append(None)

while 1:
	#terminating condition to be added!!
	message, clientAddress = serverSocket.recvfrom(1024)
	recv_pkt = unpack('IHH'+str(len(message) - 8)+'s', message)
	#print "Received packet -", recv_pkt[0]
	if recv_pkt[2] == int('1111111111111111', 2):
		break

	if random.random() > p:
		seq = recv_pkt[0]
		#print "Last in window =", last_in_window, " Received, sequence number =", seq
		recvdCheckSum = recv_pkt[1]
		header_last_part = recv_pkt[2] #contains a separator like 2 byte string of 0s and 1s
		data = recv_pkt[3]

		if protocol == "GBN":
			if seq == last_recvd + 1 and checksum(recvdCheckSum, seq, header_last_part, data):
				# means checksum is fine and the seq no. is also fine
				file_content = file_content + data
				ack(seq, clientAddress)
				last_recvd = seq
			elif seq != last_recvd + 1:
				# send the ack for the old last_recvd
				if last_recvd >= 0:
					ack(last_recvd, clientAddress)

		elif protocol == "SR":
			if seq < first_in_window:
				#old packet already processed - only ACK
				ack(seq, clientAddress)
			elif seq >= first_in_window and seq <= last_in_window and checksum(recvdCheckSum, seq, header_last_part, data):
				#packet within window, process accordingly

				if seq == first_in_window:
					#slide window
					file_content = file_content + data
					recv_buffer[first_in_window % N] = None
					received[first_in_window % N] = 0
					first_in_window = first_in_window + 1
					last_in_window = last_in_window + 1
					it = first_in_window
					while received[it % N] == 1:
						file_content = file_content + recv_buffer[it % N][3]
						recv_buffer[it % N] = None
						received[it % N] = 0
						first_in_window = first_in_window + 1
						last_in_window = last_in_window + 1
						it = first_in_window

				elif received[seq % N] == 0:
					#packet has not been buffered
					recv_buffer[seq % N] = recv_pkt
					received[seq % N] = 1

				#ACK the packet
				ack(seq, clientAddress)

	else:
		print "Packet loss, sequence number =", recv_pkt[0]



#write the data to a file
write(file_content)

