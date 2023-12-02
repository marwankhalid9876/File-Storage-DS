import os
import socket

def send_file(filename, client):
    try:
        file = open('sender_folder/'+filename, 'rb')
        data = file.read(1024)
        while data:
            client.send(data)
            data = file.read(1024)
        client.send(b'<End>')
        file.close()
        return True
    except ConnectionResetError:#If the client disconnected
        return False

def receive_write_file(filename, client):
    try:
        data = client.recv(1024)
        if data.endswith(b'<Cancel>'): # If the client cancelled the update operation
            return True # Return True because client cancelled the operation but didn't disconnect
        file = open('sender_folder/'+filename, 'wb')
        while data:
            if data.endswith(b'<End>'):
                data = data[:-5]
                file.write(data)
                break
            file.write(data)
            data = client.recv(1024)
        file.close()
        client.send(b'<Done>') #Acknowledge the client that the operation is done
        return True
    except ConnectionResetError:#If the client disconnected
        return False
    
    
print('SERVER INITIALIZING...')
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP
server.bind(('localhost', 9999))
server.listen()
print('SERVER RUNNING...')

while True:
    print('==============================================')
    client, address = server.accept()
    print(f'CLIENT {address} CONNECTED...')

    connection_opened = True
    #SERVE THIS CLIENT WITH AS MANY OPERATIONS AS HE WANTS
    while connection_opened:

        files_on_server = next(os.walk('sender_folder/'), (None, None, []))[2]  # [] if no file

        try:
            client.send(str(files_on_server).encode())#Send the list of files on the server
            operation_filename = client.recv(1024).decode()
        except ConnectionResetError:#If the client disconnected:
            print('CLIENT DISCONNECTED')
            connection_opened = False
            client.close()
            break
        print(operation_filename)
        operation_filename_list = operation_filename.split(' ', 1)
        
        try:
            operation = operation_filename_list[0].lower()
            filename = operation_filename_list[1]
        except:
            #Close the connection because the client request errors are handled at client. 
            #If the client sent an invalid request, then it means that the client is not working properly
            print('CLIENT REQUESTED INVALID OPERATION')
            connection_opened = False
            client.close()
            break
        
        print('CLIENT REQUESTED OPERATION: '+operation_filename)
        match operation:
            case 'read':
                success = send_file(filename, client)
                if not success:
                    print('CLIENT DISCONNECTED')
                    connection_opened = False
                    client.close()
                    break
                print('READ REQUEST SERVED!')
            case 'write':
                print('RECEIVING FILE...')
                success = receive_write_file(filename, client)
                if not success:
                    print('CLIENT DISCONNECTED')
                    connection_opened = False
                    client.close()
                    break
                print('WRITE REQUEST SERVED!')
            case 'update':
                print('SENDING CURRENT FILE STATUS...')
                success = send_file(filename, client)
                if not success:
                    print('CLIENT DISCONNECTED')
                    connection_opened = False
                    client.close()
                    break
                print('FILE STATUS SENT!')
                print('RECEIVING UPDATED FILE...')
                success = receive_write_file(filename, client)
                if not success:
                    print('CLIENT DISCONNECTED')
                    connection_opened = False
                    client.close()
                    break
                print('UPDATE REQUEST SERVED!')
            case 'delete':
                try:
                    os.remove('sender_folder/'+filename)
                except ConnectionResetError:
                    files_on_server = next(os.walk('sender_folder/'), (None, None, []))[2]  # [] if no file
                    client.send((str(files_on_server)).encode())
                    client.send(b'<Fail>')
                files_on_server = next(os.walk('sender_folder/'), (None, None, []))[2]  # [] if no file
                client.send((str(files_on_server)).encode())#Send the updated list of files on the server
                client.send(b'<Done>')
                print('DELETE REQUEST SERVED!')
        try:
            if(client.recv(1024).decode() == '<Exit>'):
                connection_opened = False
                client.close()
        except ConnectionResetError:
            print('CLIENT DISCONNECTED')
            connection_opened = False
            client.close()
            break
    print('CLIENT OPERATION TERMINATED...')


