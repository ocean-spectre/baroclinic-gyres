This file contains information for each run in the uniformshelf directory. Inputs for individual runs can be found in inputs, these are linked to the run directories found in run, model output for each run is found in output. input/run/output directory numbers are consistent across components. 

Run 1: Initial testing run for simulation file size, wall clock time, and for wyatt to familiarize himself with running simulations on galapagos. Uses 64 cores split 4 in x and 16 in y. Monitor frequency is daily, model state and diagnostics are output is every 10 days, and total runtime is 365 days.

Run 2: Extended initial testing run for simulations. 24 cores split 4 in x and 6 in y. Monitor frequency is daily. Model state and diagnostics are output every 30 days. Total run time is 10 years.  

Run 3: Run pickup of run 2 starting at day 3000 going until day 6000, same core split as run 3. Unfinished, continental shelf is on wrong side of domain.

Run 4: Corrected runs 2/3 to the correct continental shelf, running on oram 24 cores split 4 in x and 6 in y. State and data variables are dumped every 10 days and monitor freq is 30 days. Pickup files are written every 30 days. Total runtime is 3000 days. Will pickup 5 times for a total of 15,000 days. 

Run 5: Pickup of run 4 for days 3000-6000.
Run 6: Pickup for days 6000-9000.
Run 7: Pickup for days 9000-12000.
Run 8: Pickup for days 12000-15000.

Run 9: A second major test run in addition to the run 4-8 pickups. Making the shelf on the western boundary wider by adjusting a and b in gendata-baroclinic.py to 200 from 100. Run in 3 pickups of 5000 days each across 24 cores on oram. Total runtime will be 15000 days for comparison.
