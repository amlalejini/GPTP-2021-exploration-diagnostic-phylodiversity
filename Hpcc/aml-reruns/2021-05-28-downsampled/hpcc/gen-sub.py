'''
Generate slurm job submission scripts - one per condition
'''

import argparse, os, sys, errno, subprocess, csv
from pyvarco import CombinationCollector

seed_offset = 120000
default_num_replicates = 50
job_time_request = "10:00:00"
job_memory_request = "4G"
job_name = "diagnose"
executable = "dia_world"
base_script_filename = './base_script.txt'

SELECTION_PARAM = {
    "MULAMBDA":"0",
    "TOURNAMENT":"1",
    "FITSHARING":"2",
    "NOVELTY":"3",
    "LEXICASE":"4",
    "DOWNSAMPLED":"5",
    "COHORT":"6",
    "LEX_NOVELTY":"7"
}

DIAGNOSTIC_PARAM = {
    "EXPLOITATION":"0",
    "STRUCTURED_EXPLOITATION":"1",
    "NICHING":"2",
    "EXPLORATION":"3"
}

fixed_params= {
    "POP_SIZE":"500",
    "TARGET":"100.0",
    "ACCURACY":"0.99",
    "CREDIT":"0.0",
    "DIAGNOSTIC":DIAGNOSTIC_PARAM["EXPLORATION"],
    "SELECTION":SELECTION_PARAM["DOWNSAMPLED"],
    "MUTATE_PER":"0.007",
    "MEAN":"0.0",
    "STD":"1.0",
    "TOUR_SIZE":"8",
    "SNAP_INTERVAL":"10000",
    "PRINT_INTERVAL":"1000",
    "OUTPUT_DIR":"./",
    "LEX_EPS":"0",
    "OBJECTIVE_CNT":"100"
}

# Create combo object to collect all conditions we'll run
combos = CombinationCollector()
combos.register_var("DSLEX_PROP")
combos.add_val(
    "DSLEX_PROP",
    [
        "1.0",
        "0.5",
        "0.2",
        "0.1",
        "0.05",
        "0.02",
        "0.01"
    ]
)

prop_to_gens = {
    "1.0":"50000",
    "0.5":"100000",
    "0.2":"250000",
    "0.1":"500000",
    "0.05":"1000000",
    "0.02":"2500000",
    "0.01":"5000000"
}


'''
This is functionally equivalent to the mkdir -p [fname] bash command
'''
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def main():
    parser = argparse.ArgumentParser(description="Run submission script.")
    parser.add_argument("--data_dir", type=str, help="Where is the output directory?")
    parser.add_argument("--config_dir", type=str, help="Where is the configuration directory for experiment?")
    parser.add_argument("--replicates", type=int, default=default_num_replicates, help="How many replicates should we run of each condition?")
    parser.add_argument("--job_dir", type=str, default="./job-files", help="Where to output these job files?")

    # Load command line arguments
    args = parser.parse_args()
    config_dir = args.config_dir
    data_dir = args.data_dir
    num_replicates = args.replicates
    job_dir = args.job_dir

    # Load in the base slurm file
    with open(base_script_filename, 'r') as fp:
        base_sub_script = fp.read()

    # Get list of all combinations to run
    combo_list = combos.get_combos()
    # Calculate how many jobs we have, and what the last id will be
    num_jobs = num_replicates * len(combo_list)
    print(f'Generating {num_jobs} across {len(combo_list)} files!')

    cur_job_id = 0
    cond_i = 0
    for condition_dict in combo_list:
        cur_seed = seed_offset + (cur_job_id * num_replicates)
        filename_prefix = f"RUN_C{cond_i}"
        file_str = base_sub_script
        file_str = file_str.replace("<<TIME_REQUEST>>", job_time_request)
        file_str = file_str.replace("<<ARRAY_ID_RANGE>>", f"1-{num_replicates}")
        file_str = file_str.replace("<<MEMORY_REQUEST>>", job_memory_request)
        file_str = file_str.replace("<<JOB_NAME>>", job_name)
        file_str = file_str.replace("<<CONFIG_DIR>>", config_dir)
        file_str = file_str.replace("<<EXEC>>", executable)
        file_str = file_str.replace("<<JOB_SEED_OFFSET>>", str(cur_seed))

        file_str = file_str.replace(
            "<<RUN_DIR>>",
            os.path.join(data_dir, f"{filename_prefix}_"+"${SEED}")
        )

        # Add fixed parameter information
        run_param_info = {param:fixed_params[param] for param in fixed_params}
        sample_prop = condition_dict["DSLEX_PROP"]
        run_param_info["DSLEX_PROP"] = sample_prop
        run_param_info["MAX_GENS"] = prop_to_gens[sample_prop]

        fields = list(run_param_info.keys())
        fields.sort()
        run_params = " ".join([f"-{field} {run_param_info[field]}" for field in fields])
        run_commands = ""
        run_commands += f'RUN_PARAMS="{run_params}"\n'
        run_commands += 'echo "./${EXEC} ${RUN_PARAMS}" > cmd.log\n'
        run_commands += './${EXEC} ${RUN_PARAMS} > run.log\n'

        file_str = file_str.replace("<<RUN_COMMANDS>>", run_commands)

        mkdir_p(job_dir)
        with open(os.path.join(job_dir, f'{filename_prefix}.sb'), 'w') as fp:
            fp.write(file_str)
        cur_job_id += 1
        cond_i += 1

if __name__ == "__main__":
    main()
