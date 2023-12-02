import socket
import os

def check_filename_exists(filename, filenames_on_server):
    if filename not in filenames_on_server:
        print('File not found, please try again')
        return False
    return True


def read_file_from_server(filename):
    file = open(filename, 'wb')
    file_bytes = b""
    while True:
        data = client.recv(1024)
        if data[-5:] == b'<End>':
            break
        else:
            file_bytes += data
    file.write(file_bytes)
    file.close()
    os.startfile(filename)

def write_file_to_server(filename):
    try:
        file = open(filename, 'rb')
        data = file.read(1024)
        while data:
            client.send(data)
            data = file.read(1024)
        client.send(b'<End>')
        file.close()
        return True
    except:
        print('An error happened, please try again')
        return False

def prompt_user(filenames_on_server):
    print('==============================================')
    print('These are the files currently in the server: ')
    print(filenames_on_server)
    print('==============================================')
    print('What operation would you like to do?')
    print('For reading a file, write "read" then the file name')
    print('For writing a file, write "write" then the file name')
    print('For updating a file, write "update" then the file name')
    print('For deleting a file, write "delete" then the file name')

def have_more_operations():
    if input('Do you want to do more operations? (y/n) \n') == 'y':
        return True
    return False


print('Connecting to the server...')
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 9999))



while True:


    filenames_on_server = eval(client.recv(4096).decode())

    while True: #loop until valid input
        try:
            # Print the files on the server and the operations that can be done
            prompt_user(filenames_on_server)
            operation_filename = input('Please enter your operation: \n')
            operation_filename_list = operation_filename.split(' ', 1)
            operation = operation_filename_list[0].lower()
            if operation == 'exit': break
            filename = operation_filename_list[1]
            if operation not in ['read', 'write', 'update', 'delete']:
                raise Exception
            if operation in ['read','update','delete']  and check_filename_exists(filename, filenames_on_server) == False:
                print('This file does not exist, please enter a file from the list:')
                raise Exception
            if operation == 'write' and not os.path.exists(filename):
                raise Exception
            if operation == 'write' and filename in filenames_on_server:
                if input('File already exists on the server, do you want to overwrite it? (y/n) \n') != 'y':
                    continue #if user doesn't want to overwrite, re-prompt user for another operation
            if operation == 'delete' and input('Are you sure you want to delete this file? (y/n) \n') != 'y':
                continue #if user doesn't want to delete, re-prompt user for another operation
            break #break out of loop if valid input
        #handle if invalid input
        except:
            print('Invalid input, please try again')
    
    if operation == 'exit': break    

    match operation:
        case 'read':
            client.send(operation_filename.encode())
            read_file_from_server(filename)

            if input('Do you want to do more operations? (y/n) \n') == 'y':
                client.send(b'<Continue>')#inform server that I want to do more operations
                continue
            break
        case 'write':
            client.send(operation_filename.encode())
            success = write_file_to_server(filename)
            if not success:
                continue
            print(client.recv(1024).decode())#print the server response
            if input('Do you want to do more operations? (y/n) \n') == 'y':
                client.send(b'<Continue>')#inform server that I want to do more operations
                continue
            break
        case 'update':                
            client.send(operation_filename.encode())
            print('The file will now be opened automatically, please make your changes and save the file')
            read_file_from_server(filename)
            while True:
                user_done = input('Once you are done, please close the file and enter "y" \n') == 'y'
                if user_done:
                    write_file_to_server(filename)
                    print(client.recv(1024).decode())#print the server response
                    break
                else: 
                    if input('Are you sure you want to exit without updating the file on the server? (y/n) \n') == 'y':
                        client.send(b'<Cancel>')#inform server that update was cancelled
                        break
            
            if input('Do you want to do more operations? (y/n) \n') == 'y':
                client.send(b'<Continue>')#inform server that I want to do more operations
                continue
            break
        case 'delete':
            if check_filename_exists(filename, filenames_on_server) == False:
                continue
            client.send(operation_filename.encode())
            print(client.recv(4096).decode())#new Files on server
            print(client.recv(1024).decode())#print the server response <Done>   
                              
            if input('Do you want to do more operations? (y/n) \n') == 'y':
                client.send(b'<Continue>')#inform server that I want to do more operations
                continue
            break

 
        case _:#handle if invalid operation
            print('Invalid input, please try again')
            continue

client.send('<Exit>'.encode())
client.close()


# file_size = client.recv(1024).decode()
# print(file_size)


            

