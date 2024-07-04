import os

# Set your mount point
mount_point = "/Users/tarandeepsinghkohli/Desktop/JIO_Cloud/mnt/google_drive"

# List all files in the mount point
def list_files_in_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            print(os.path.join(root, file))

list_files_in_directory(mount_point)
