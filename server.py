import os
import socket
import pickle

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
        send_tree_to_client(client)
        client.send(b'<Done>') #Acknowledge the client that the operation is done
        return True
    except ConnectionResetError:#If the client disconnected
        return False
    
def build_directory_tree(directory):
    result = {}
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            result[item] = build_directory_tree(item_path)
        else:
            result[item] = None  # You can set it to a specific value or leave it as None
    return result

def send_tree_to_client(client):
    tree = build_directory_tree('sender_folder/')
    tree = pickle.dumps(tree)
    client.sendall(tree)
    
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

    try: #First, send the tree of the directory and subdirectories to the client
        #Send the tree of directories and files on the server
        send_tree_to_client(client)
    except ConnectionResetError:#If the client disconnected:
        print('CLIENT DISCONNECTED')
        connection_opened = False
        client.close()
        continue

    subfolder = ''
    #SERVE THIS CLIENT WITH AS MANY OPERATIONS AS HE WANTS
    while connection_opened:
        
        #send the list of files on the server
        files_on_server = next(os.walk('sender_folder/'+subfolder), (None, None, []))[2]  # [] if no file
        
        try:
            # #Send the list of files on the server
            # client.send(str(files_on_server).encode())
            # #send the list of subfolders on the server
            # all_subdirectories = [x[0] for x in os.walk('sender_folder/'+subfolder)]
            operation_path = client.recv(1024).decode() #Receive the operation and filename from the client
        except ConnectionResetError:#If the client disconnected:
            print('CLIENT DISCONNECTED')
            connection_opened = False
            client.close()
            break
        print(operation_path)
        operation_path_list = operation_path.split(' ', 1)
        
        try:
            operation = operation_path_list[0].lower()
            #substring path to remove first 5 characters "root/"
            path = operation_path_list[1][5:]
            print(path)
        except:
            #Close the connection because the client request errors are handled at client. 
            #If the client sent an invalid request, then it means that the client is not working properly
            print('CLIENT REQUESTED INVALID OPERATION')
            connection_opened = False
            client.close()
            break
        
        print('CLIENT REQUESTED OPERATION: '+operation_path)
        match operation:
            case 'read':
                success = send_file(path, client)
                if not success:
                    print('CLIENT DISCONNECTED')
                    connection_opened = False
                    client.close()
                    break
                print('READ REQUEST SERVED!')
            case 'write':
                print('RECEIVING FILE...')
                success = receive_write_file(path, client)
                if not success:
                    print('CLIENT DISCONNECTED')
                    connection_opened = False
                    client.close()
                    break
                print('WRITE REQUEST SERVED!')
            case 'update':
                print('SENDING CURRENT FILE STATUS...')
                success = send_file(path, client)
                if not success:
                    print('CLIENT DISCONNECTED')
                    connection_opened = False
                    client.close()
                    break
                print('FILE STATUS SENT!')
                print('RECEIVING UPDATED FILE...')
                success = receive_write_file(path, client)
                if not success:
                    print('CLIENT DISCONNECTED')
                    connection_opened = False
                    client.close()
                    break
                print('UPDATE REQUEST SERVED!')
            case 'delete':
                try:
                    os.remove('sender_folder/'+path)
                except ConnectionResetError:
                    send_tree_to_client(client)
                    client.send(b'<Fail>')
                send_tree_to_client(client)
                client.send(b'<Done>')
                print('DELETE REQUEST SERVED!')
            case 'create':
                pass
            case 'cd':
                pass

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


