import os
import ctypes
import psutil
import re
import glob
import shutil
import subprocess
import time
import io
from STPK import STPK

# Define the paths
rpcs3_path = "C:/Users/defin/Downloads/rpcs3-v0.0.27-14783-0178b209_win64/rpcs3.exe"
character_folder = "C:/Users/defin/Downloads/rpcs3-v0.0.27-14783-0178b209_win64/dev_hdd0/game/SCEEXE000/USRDIR/00.99/character"
savestate_path = "C:/Users/defin/Downloads/rpcs3-v0.0.27-14783-0178b209_win64/savestates/used_SCEEXE000_RIGHT_BEFORE_BATTLE.SAVESTAT"

# Define the standard names
ioram_standard_name = "00_goku0_model1_ioram.pak.scz"
vram_standard_name = "00_goku0_model1_vram.pak.scz"

# Get the list of ioram and vram files, excluding the standard names
ioram_files = sorted([file for file in glob.glob(os.path.join(character_folder, "*model*_ioram.pak.scz")) if "00_goku0_model1_ioram.pak.scz" not in file])
vram_files = sorted([file for file in glob.glob(os.path.join(character_folder, "*model*_vram.pak.scz")) if "00_goku0_model1_vram.pak.scz" not in file])


def find_signature(data, signature):
    return [i for i in range(len(data)) if data[i:i+len(signature)] == signature]

def dump_ram(iteration, starting_address, upper_limit_address, ram_type):
    print("Starting RAM dump...")
    
    process_name = "rpcs3.exe"
    search_string = b"STPK"
    
    print("Finding the process...")

    # Find the process
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            pid = proc.info['pid']
            break
    else:
        return
    
    print("Opening the process...")
    # Open the process
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    process = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)

    # Define the MEMORY_BASIC_INFORMATION structure
    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_size_t),
            ("AllocationBase", ctypes.c_size_t),
            ("AllocationProtect", ctypes.c_ulong),
            ("RegionSize", ctypes.c_size_t),
            ("State", ctypes.c_ulong),
            ("Protect", ctypes.c_ulong),
            ("Type", ctypes.c_ulong)
        ]

    mbi = MEMORY_BASIC_INFORMATION()
    current_address = ctypes.c_size_t(starting_address)
    buffer_data = b""
    
    print("Reading process memory...")
    
    while current_address.value < upper_limit_address and ctypes.windll.kernel32.VirtualQueryEx(process, current_address, ctypes.byref(mbi), ctypes.sizeof(mbi)):
        buffer = ctypes.create_string_buffer(mbi.RegionSize)
        bytes_read = ctypes.c_size_t(0)
        ctypes.windll.kernel32.ReadProcessMemory(process, ctypes.c_size_t(mbi.BaseAddress), buffer, mbi.RegionSize, ctypes.byref(bytes_read))
        buffer_data += buffer.raw
        current_address.value += mbi.RegionSize
        
        

    ctypes.windll.kernel32.CloseHandle(process)
    
    print("Finding matches...")

    matches = [m.start() for m in re.finditer(search_string, buffer_data)]
    if matches:
        if ram_type == "ioram":
            selected_matches = matches[7:8] if len(matches) > 7 else None  # Select the 8th match for ioram
        elif ram_type == "vram":
            selected_matches = matches[:3] if len(matches) > 3 else None  # Select the first 3 matches for vram

        if selected_matches is not None:
            for i, match in enumerate(selected_matches):
                print(f"STPK found at offset {match} in buffer_data")
                # Find the next STPK or the end of the buffer_data
                end = matches[matches.index(match) + 1] if (matches.index(match) + 1) < len(matches) else len(buffer_data)
                found_data = buffer_data[match:end]

                # Export the found data to a file
                print(f"Exporting data to output_{ram_type}_{i}.bin...")
                with open(f"iteration_{iteration}/output_{ram_type}_{i}.bin", "wb") as f:
                    f.write(found_data)
    else:
         print("No matches found in process memory.")

    print("RAM dump complete.")



def split_stpk(iteration, ram_type):
    print("Starting STPK split...")

    if ram_type == "ioram":
        num_files = 1
    elif ram_type == "vram":
        num_files = 1

    for i in range(num_files):
        # Read the RAM dump
        print(f"Reading RAM dump from iteration_{iteration}/output_{ram_type}_{i}.bin...")
        with open(f'iteration_{iteration}/output_{ram_type}_{i}.bin', 'rb') as f:
            ram_dump = f.read()

        # Create an STPK object and write it to a file
        stpk_obj = STPK()

        # Create a BytesIO object from the data
        stpk_data = io.BytesIO(ram_dump)

        # Read the STPK data
        stpk_obj.read(stpk_data)

        # Write the STPK data to an output file
        print(f"Writing STPK data to iteration_{iteration}/my_output_{ram_type}_{i}.stpk...")
        with open(f'iteration_{iteration}/my_output_{ram_type}_{i}.stpk', 'wb') as f:
            stpk_obj.write(f)

    print("STPK split complete.")



# Main procedure
def main():
    # Check if there are equal numbers of ioram and vram files
    if len(ioram_files) != len(vram_files):
        print("Mismatch in number of ioram and vram files")
        exit(1)
    # Set a flag to indicate when to start processing
    start_processing = False

    # For each pair of ioram and vram files
    for iteration, (ioram_file, vram_file) in enumerate(zip(ioram_files, vram_files), start=1):
        print(f"Processing {ioram_file} and {vram_file}")
        
        # Check if we have reached the starting point
        if '05_tien_model1_ioram.pak.scz' in ioram_file and '05_tien_model1_vram.pak.scz' in vram_file:
            start_processing = True

        # If we have not reached the starting point, skip this iteration
        if not start_processing:
            continue
        
        # Create a new directory for this iteration
        os.makedirs(f"iteration_{iteration}")
        
        # Swap the ioram and vram files with the standard names
        temp_ioram = os.path.join(character_folder, "temp_ioram.pak.scz")
        temp_vram = os.path.join(character_folder, "temp_vram.pak.scz")
        os.rename(ioram_file, temp_ioram)
        os.rename(vram_file, temp_vram)
        os.rename(os.path.join(character_folder, ioram_standard_name), ioram_file)
        os.rename(os.path.join(character_folder, vram_standard_name), vram_file)
        os.rename(temp_ioram, os.path.join(character_folder, ioram_standard_name))
        os.rename(temp_vram, os.path.join(character_folder, vram_standard_name))

        print("Running rpcs3...")
        # Run rpcs3
        rpcs3_process = subprocess.Popen([rpcs3_path, "--no-gui", "--savestate", savestate_path])

        # Wait for a while for rpcs3 to load the character
        print("Waiting for rpcs3 to load the character...")
        time.sleep(23)  # Adjust this as needed

        # Run the RAM dump function for ioram
        print("Dumping RAM for ioram...")
        dump_ram(iteration, 0x24000000, 0x24C5F780, "ioram")  # ioram addresses

        # Wait for a while for the RAM dump to complete
        print("Waiting for the ioram RAM dump to complete...")
        time.sleep(6)  # Adjust this as needed

        # Run the STPK split function for ioram
        print("Splitting ioram STPK...")
        split_stpk(iteration, "ioram")

        # Run the RAM dump function for vram
        print("Dumping RAM for vram...")
        dump_ram(iteration, 0x100000000, 0x180000000, "vram")  # vram addresses

        # Wait for a while for the RAM dump to complete
        print("Waiting for the vram RAM dump to complete...")
        time.sleep(6)  # Adjust this as needed

        # Run the STPK split function for vram
        print("Splitting vram STPK...")
        split_stpk(iteration, "vram")


        # Swap the standard ioram and vram files back to their original names
        print("Restoring original ioram and vram files...")
        os.rename(ioram_file, temp_ioram)
        os.rename(vram_file, temp_vram)
        os.rename(os.path.join(character_folder, ioram_standard_name), ioram_file)
        os.rename(os.path.join(character_folder, vram_standard_name), vram_file)
        os.rename(temp_ioram, os.path.join(character_folder, ioram_standard_name))
        os.rename(temp_vram, os.path.join(character_folder, vram_standard_name))

        # Close rpcs3
        print("Terminating rpcs3 process...")
        rpcs3_process.terminate()


# Run main
if __name__ == "__main__":
    main()

