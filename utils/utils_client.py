import socket
import os
import pickle
import subprocess
import sys

import warnings
warnings.filterwarnings("ignore")

def check_filename_exists(filename, filenames_on_server):
    if filename not in filenames_on_server:
        print('File not found, please try again')
        return False
    return True


def read_file_from_server(filename, client):
    if not os.path.exists('locals'):
        os.makedirs('locals')

    filename = f"locals/{filename}"
    with open(filename, 'w') as f: 
        file_bytes = ""
        while True:
            data = client.recv(1024).decode()
            if data[-5:] == '<End>':
                break
            else:
                file_bytes += data
        f.write(file_bytes)
        print('File received successfully')

    # if sys.platform.startswith('win32'):
    #     os.startfile(filename)
    # elif sys.platform.startswith('darwin'):
    #     subprocess.run(('open', filename), check=True)
    # elif sys.platform.startswith('linux'):
    #     subprocess.run(('xdg-open', filename), check=True)


def write_file_to_server(file_path, client):
    try:
        filename = file_path.split('/')[-1]
        with open(f"locals/{filename}", 'rb') as file:
            data = file.read(1024)
            while data:
                client.send(data)
                data = file.read(1024)
            client.send('<End>'.encode())
    except:
        print('An error happened, please try again')


def get_directory_from_path(directories_dict, path):
    if path == 'root':
        return directories_dict
    path_list = path.split('/')
    path_list = path_list[1:]
    current_dict = directories_dict
    for directory in path_list:
        current_dict = current_dict[directory]
    return current_dict


def prompt_user(directories_dict, current_directory):
    print('==============================================')
    print("These are the files currently in the server's "  + current_directory + " directory: ")
    current_directory_dict = get_directory_from_path(directories_dict, current_directory)
    print_directory_tree(current_directory_dict)
    print('==============================================')
    print('What operation would you like to do?')
    print('For reading a file, write "read" then the file name')
    print('For writing a file, write "write" then the file name')
    print('For updating a file, write "update" then the file name')
    print('For deleting a file, write "delete" then the file name')
    print('For changing directory, write "cd" then the directory name')
    print('For exiting, write "exit"')
    print('Please note that the file name must be the full path from the current directory')


def have_more_operations():
    if input('Do you want to do more operations? (y/n) \n') == 'y':
        return True
    return False


def print_directory_tree(directory_tree, indent=0):
    for key, value in directory_tree.items():
        if value is None:
            print('  ' * indent + f'- {key} (file)')
        else:
            print('  ' * indent + f'- {key} (directory)')
            print_directory_tree(value, indent + 1)


def cd_back_steps(current_directory , path):
    path_list = path.split('/')
    for step in path_list:
        if step == '..':
            current_directory = '/'.join(current_directory.split('/')[:-1])
            path_list = path_list[1:]
    return current_directory, '/'.join(path_list)


def is_valid_directory(directories_dict, current_directory, directory_path):
    #get rid of back steps
    current_directory, directory_path = cd_back_steps(current_directory, directory_path)
    if directory_path == '': return True #if user entered only back steps
    #check that directory exists
    directory_name_list = list(directory_path.split('/'))
    for directory in directory_name_list:
        if directory not in list(get_directory_from_path(directories_dict, current_directory).keys()):
            print('This directory does not exist, please enter a directory from the list:')
            return False
        else:
            current_directory = current_directory + '/' + directory
    #check that last item in path is a directory not a filename
    if get_directory_from_path(directories_dict, current_directory) is None:
        print('This is a file, please enter a directory from the list:')
        return False
    return True


def is_valid_path(directories_dict, current_directory, path):
    #get rid of back steps
    current_directory, directory_path = cd_back_steps(current_directory, path)
    if directory_path == '': return True #if user entered only back steps
    #check that directory/file exists
    path_list = path.split('/')
    path_list = path_list
    for directory in path_list:
        if directory not in list(get_directory_from_path(directories_dict, current_directory).keys()):
            return False
        else:
            current_directory = current_directory + '/' + directory
    return True


def receive_tree_from_server(client):
    # send get tree request
    # client.send(b'<Get Tree>')
    directories_dict = client.recv(4096)
    directories_dict = pickle.loads(directories_dict)
    return directories_dict


print('Connecting to the server...')
# client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# client.connect(('localhost', 9999))


def client_main_app(client):
    current_directory = 'root'
    #Once connected, the client receives the directory tree from the server
    # directories_dict = receive_tree_from_server(client)
    directories_dict = client.directories_dict #receive_tree_from_server(client)
    while True:
        while True: #loop until valid input
            # directories_dict = receive_tree_from_server(client)
            try:
                # Print the files on the server and the operations that can be done
                prompt_user(directories_dict, current_directory)
                operation_filename = input('Please enter your operation: \n')
                operation_filename_list = operation_filename.split(' ', 1)
                operation = operation_filename_list[0].lower()
                if operation == 'exit': break
                filename = operation_filename_list[1]
                if operation not in ['read', 'write', 'update', 'delete','cd']:
                    raise Exception
                if operation in ['read','update','delete'] and not is_valid_path(directories_dict, current_directory, filename):
                    print('This file does not exist, please enter a file from the list')
                    raise Exception
                if operation == 'write' and not os.path.exists(filename):#check that file exists on client side
                    raise Exception
                if operation == 'write' and is_valid_path(directories_dict, current_directory, filename): 
                    if input('File already exists on the server, do you want to overwrite it? (y/n) \n') != 'y':
                        continue #if user doesn't want to overwrite, re-prompt user for another operation
                if operation == 'delete' and input('Are you sure you want to delete this file? (y/n) \n') != 'y':
                    continue #if user doesn't want to delete, re-prompt user for another operation
                if operation == 'cd'and not is_valid_directory(directories_dict, current_directory, filename):
                        raise Exception
                break #break out of loop if valid input
            #handle if invalid input
            except:
                print('Invalid input, please try again')
            
        if operation == 'exit': sys.exit()    

        match operation:
            case 'read':
                operation_path = operation + ' ' + current_directory + '/' + filename
                client.send(operation_path.encode())
                read_file_from_server(filename, client)

                if input('Do you want to do more operations? (y/n) \n') == 'y':
                    client.send(b'<Continue>')#inform server that I want to do more operations
                    continue
                break
            case 'write':
                operation_path = operation + ' ' + current_directory + '/' + filename
                client.send(operation_path.encode())
                success = write_file_to_server(filename, client)
                if not success:
                    print('Error! Please try again')
                    continue
                directories_dict = receive_tree_from_server(client)
                print("These are the files currently in the server after writing"  + str(directories_dict) + " directory: ")
                print(client.recv(1024).decode())#print the server response
                if input('Do you want to do more operations? (y/n) \n') == 'y':
                    client.send(b'<Continue>')#inform server that I want to do more operations
                    continue
                break
            case 'update':         
                operation_path = operation + ' ' + current_directory + '/' + filename       
                client.send(operation_path.encode())
                print('The file will now be opened automatically, please make your changes and save the file')
                read_file_from_server(operation_path, client)
                while True:
                    user_done = input('Once you are done, please close the file and enter "y" \n') == 'y'
                    if user_done:
                        write_file_to_server(filename, client)
                        directories_dict = receive_tree_from_server(client)        
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
                # if check_filename_exists(filename, filenames_in_directory) == False:
                #     continue
                operation_path = operation + ' ' + current_directory + '/' + filename
                client.send(operation_path.encode())
                directories_dict = receive_tree_from_server(client)
                print("These are the files currently in the server "  + str(directories_dict) + " directory: ")
                print(client.recv(1024).decode())#print the server response <Done>   
                                
                if input('Do you want to do more operations? (y/n) \n') == 'y':
                    client.send(b'<Continue>')#inform server that I want to do more operations
                    continue
                break
            case 'cd':
                #get rid of back steps
                current_directory, filename = cd_back_steps(current_directory, filename)
                #if there is a path after stepbacks, add it to the current directory
                if filename != '':
                    current_directory += '/' + filename
                continue
            case _:#handle if invalid operation
                print('Invalid input, please try again2')
                continue

    client.send('<Exit>'.encode())
    client.close()


# file_size = client.recv(1024).decode()
# print(file_size)


            

