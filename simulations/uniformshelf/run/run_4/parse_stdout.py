import re
import pandas as pd

# Function to parse MITgcm monitoring statistics, separating blocks
def parse_mitgcm_monitor(file_path):
    monitor_pattern = re.compile(r"^\(PID\.TID\s+\d+\.\d+\)\s+%MON\s+(\S+)\s+(.*)")

    monitor_blocks = []
    current_block = []
    inside_block = False

    with open(file_path, 'r') as file:
        for line in file:
            match = monitor_pattern.match(line)
            if match:
                if not inside_block:
                    # Start of a new block
                    inside_block = True
                    current_block = {}

                field_name = match.group(1)
                value = match.group(2).strip()

                # Attempt to parse value as a float if possible
                try:
                    value = float(value)
                except ValueError:
                    pass

                current_block[field_name] = value
            else:
                if inside_block: # We've reached the end of a block
                    inside_block = False
                    monitor_blocks.append(current_block)

    return pd.DataFrame(monitor_blocks)

if __name__ == "__main__":
    # Interactive file path input for the user
    file_path = "./STDOUT.0001" #input("Enter the path to the MITgcm standard output file: ").strip()

    # Parse the file for monitoring data
    monitor_data = parse_mitgcm_monitor(file_path)

    # Display the parsed monitoring statistics
    print(monitor_data)
