from datetime import datetime
import os

cluster=os.getenv('cluster', 'galapagos')
simulation=os.getenv('simulation', 'uniformshelf')
cwd = os.getcwd()

# make sure to change simulation number if relying on default instead of environment variable
simulation_number = 5

outdir=os.getenv('outdir', f'{cwd}/simulations/{simulation}/output/output_{simulation_number}')

time_file = f'{outdir}/run_info.txt'

# Make the output directory if it does not exist
if not os.path.exists(outdir):
    os.makedirs(outdir)

current_time = datetime.now()

if not os.path.exists(time_file):
    with open(time_file, "w") as file:
        file.write(f"{current_time.strftime("%Y-%m-%d %H:%M:%S")}")
else:
    with open(time_file, "r+") as file:
        
        # calculate the elapsed simulation time
        start_time = file.readline()
    
        start_time_datetime = datetime.strptime(start_time.strip(), "%Y-%m-%d %H:%M:%S")
        elapsed_time = current_time - start_time_datetime
        
        file.seek(0)
        file.truncate()
        file.write(f"Total Runtime: {str(elapsed_time).split('.')[0]}\n") # split to avoid microseconds in log