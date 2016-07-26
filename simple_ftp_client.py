import sys
import signal
import time
from socket import *
import threading
from struct import *

# python sender.py server-host-name server-port# file-name N MSS

if len(sys.argv) != 7:
	print "Usage - python sender.py server-host-name server-port# file-name N MSS GBN/SR"
	exit(0)

server_host_name = sys.argv[1]
server_port = int(sys.argv[2])
file_name = sys.argv[3]
N = int(sys.argv[4])
MSS = int(sys.argv[5])
protocol = sys.argv[6]
#MAX_BYTE = 256
TIMEOUT = 3 # x 0.2 msecs

seq_num = 0
first_in_window = -1
last_in_window = -1
last_acked = -1
num_acked = -1

#seek_val = 0
f = open(file_name, 'r')

send_complete = 0 # indicates if file has been read entirely
ack_complete = 0 # indicates all packets have been ACKed

#ack_complete will be set to 1 in other thread if send_complete=1 and last_acked = last_in_window

send_buffer = [] # of size N (use %N to access)
timeout_timers = [] # of size N
acked = [] # of size N

clientSocket = socket(AF_INET, SOCK_DGRAM)
lock = threading.Lock()

def rdt_send():
	#func to read file name byte-by-byte
	#set send_complete = 1 to indicate file has been read entirely
	global send_complete
	global f

	f.seek(0, 1)
	next_byte = f.read(1)
	if next_byte == '':
		send_complete = 1
		f.close()
	return next_byte


def get_message():
	#func to read MSS bytes from rdt_send func
	global send_complete
	global MSS

	mss_string = ""
	while (len(mss_string) < MSS) and send_complete == 0:
		mss_string = mss_string + rdt_send()

	return mss_string


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
#end of func


def resend_pkts():
	#func to send packets from first_in_window to last_in_window
	global timeout_timers
	global last_in_window
	global first_in_window
	global server_host_name
	global server_port
	global N
	global MSS
	global send_buffer
	global clientSocket
	global TIMEOUT

	it = first_in_window
	while it <= last_in_window:
		if send_buffer[it % N] != None:
			send_pkt = send_buffer[it % N]
			#print "-----", server_host_name, server_port, str(it % N), send_pkt + "-----"
			#send packet
			clientSocket.sendto(send_pkt, (server_host_name, server_port))
			timeout_timers[it % N] = TIMEOUT
		it = it + 1
#end of func


def signal_handler(signum, _):
	#decrement value in all timeout_timers
	global timeout_timers
	global N
	global first_in_window
	global last_in_window
	global send_buffer
	global lock

	if ack_complete == 1:
		return

	if protocol == "GBN":
		for i, eachtimer in enumerate(timeout_timers):
			timeout_timers[i] = eachtimer - 1

		if len(timeout_timers)>(first_in_window % N) and timeout_timers[first_in_window % N] == 0:
			print "Timeout, sequence number =", first_in_window
			lock.acquire()
			resend_pkts()
			lock.release()

	elif protocol == "SR":
		it = first_in_window
		while it <= last_in_window:
			timeout_timers[it % N] = timeout_timers[it % N] - 1
			lock.acquire()
			if timeout_timers[it % N] <= 0 and send_buffer[it % N] != None:
				#timed out - resend packet
				print "Timeout, sequence number =", it
				send_pkt = send_buffer[it % N]
				clientSocket.sendto(send_pkt, (server_host_name, server_port))
				timeout_timers[it % N] = TIMEOUT
			lock.release()
			it = it + 1
#end of func


def getACKs():
	global ack_complete
	global send_complete
	global last_acked
	global last_in_window
	global first_in_window
	global send_buffer
	global N
	global clientSocket
	global acked
	global num_acked

	if protocol == "GBN":
		while ack_complete == 0:
			#recv ACK from socket in recv_pkt
			recv_pkt, serverAddress = clientSocket.recvfrom(8)
			recv_ack = unpack('IHH', recv_pkt)
			ack_num = recv_ack[0]
			if ack_num == last_acked + 1:
				#print "ACKed, sequence number =", ack_num
				lock.acquire()
				send_buffer[ack_num % N] = None
				last_acked = last_acked + 1
				first_in_window = first_in_window + 1
				lock.release()

			#terminating condition
			if send_complete == 1 and last_acked >= last_in_window:
				ack_complete = 1

	elif protocol == "SR":
		while ack_complete == 0:
			#recv ACK from socket in recv_pkt
			recv_pkt, serverAddress = clientSocket.recvfrom(8)
			recv_ack = unpack('IHH', recv_pkt)
			ack_num = recv_ack[0]
			#print "First in window =", first_in_window, " ACKed, sequence number =", ack_num
			#print "First in window =", first_in_window
			if ack_num == first_in_window:
				#slide_window
				lock.acquire()
				acked[first_in_window % N] = 0
				send_buffer[first_in_window % N] = None
				lock.release()
				num_acked = num_acked + 1
				first_in_window = first_in_window + 1
				it = first_in_window
				while acked[it % N] == 1:
					lock.acquire()
					acked[it % N] = 0
					send_buffer[it % N] = None
					lock.release()
					num_acked = num_acked + 1
					first_in_window = first_in_window + 1
					it = first_in_window
			elif ack_num > first_in_window and ack_num <= last_in_window:
				acked[ack_num % N] = 1

			#terminating condition
			if send_complete == 1 and num_acked >= last_in_window:
				ack_complete = 1


def create_fin_packet():
	header_last_part = int('1111111111111111', 2)
	checksum = int('0000000000000000', 2)
	fin_pkt = pack('IHH', seq_num, checksum, header_last_part)
	return fin_pkt


#set_global()

#start other thread to listen to ACKs
t = threading.Thread(target = getACKs, args = ())
t.start()

#starting timer and signal handler
signal.signal(signal.SIGALRM, signal_handler)
signal.setitimer(signal.ITIMER_REAL, 0.01, 0.01)

for i in range(N):
	acked.append(0)

startTime = time.time()

first_in_window = 0
while send_complete == 0:
	to_send = last_in_window + 1
	data = get_message()
	#header_last_part = chr(int('01010101', 2)) + chr(int('01010101', 2))
	header_last_part = int('0101010101010101', 2)
	calc_cs = pack('IH'+str(len(data))+'s', seq_num, header_last_part, data)
	checksum = calc_checksum(calc_cs)
	send_pkt = pack('IHH'+str(len(data))+'s', seq_num, checksum, header_last_part, data)

	if to_send < N:
		send_buffer.append(send_pkt)
		timeout_timers.append(TIMEOUT)
	else:
		send_buffer[to_send % N] = send_pkt
		timeout_timers[to_send % N] = TIMEOUT

	#send packet
	clientSocket.sendto(send_pkt, (server_host_name, server_port))

	last_in_window = last_in_window + 1
	seq_num = seq_num + 1
	while (last_in_window - first_in_window) >= (N-1):
		#do nothing - busy wait
		pass
	#end of inner while
#end of outer while

while ack_complete == 0:
	# busy wait for all acks to return
	pass

clientSocket.sendto(create_fin_packet(), (server_host_name, server_port))
clientSocket.close()

#print "For MSS =", str(MSS), " Total time taken to transfer =", str(time.time() - startTime)

