from pathlib import Path
import os

cluster=os.getenv('cluster', 'galapagos')
simulation=os.getenv('simulation', 'uniformshelf')
cwd = os.getcwd()

# make sure to change simulation number if relying on default instead of environment variable
simulation_number = 5

outdir=os.getenv('outdir', f'{cwd}/simulations/{simulation}/output/output_{simulation_number}')

size_file = f'{outdir}/run_info.txt'

output_path = Path(outdir)

size_bytes = 0.0

for f in output_path.rglob('*'):
    if f.is_file():
        size_bytes += f.stat().st_size
        
size_bytes = size_bytes / (1024**3) # convert to GB

with open(size_file, "a") as file:
    file.write(f"Total size of output directory: {size_bytes} GB\n")