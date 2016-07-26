# gobackN_selective_repeat_ftp
A FTP server implementation using Go Back N and Selective Repeat ARQ schemes

The project has Go-Back-N and Selective Repeat protocol coded and the required protocol can be run by passing the appropriate parameters when calling the python code.

The receiver (server) must be run first and then the sender (client) must be run

Protocol IDs:
GBN – Go-Back-N
SR – Selective Repeat

The code can be run using the following command for Go-Back-N (GBN):
Server: 
`python simple_ftp_server.py <port num> <file name> <probability of failure> <protocol> `

Eg: `python simple_ftp_server.py 7735 file_to_copy.txt 0.05 GBN`

Client: 
`python simple_ftp_client.py <server IP> <server port> <file name> <window size> <max segment size> <protocol>`

Eg: `python simple_ftp_client.py 152. 46.16.115 7735 copied_to_file.txt 512 500 GBN`

The code can be run using the following command for Selective Repeat (SR):
Server: 
`python simple_ftp_server.py <port num> <file name> <probability of failure> <protocol> <window size>`

Eg: `python simple_ftp_server.py 7735 file_to_copy.txt 0.05 SR 512`

Client: 
`python simple_ftp_client.py <server IP> <server port> <file name> <window size> <max segment size> <protocol>`

Eg: `python simple_ftp_client.py 152. 46.16.115 7735 copied_to_file.txt 512 500 SR`


Note:
Difference between the running of the 2 protocols is to specify GBN or SR and in case of using SR, the window size also needs to be passed as an argument. The window size should be the same as that on the sender side.

