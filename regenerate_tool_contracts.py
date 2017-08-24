#!/usr/bin/env python

"""
Re-generate all tool contracts in the registered-tool-contracts directory,
using automatically determined commands.  Assumes that all tools/modules not
explicitly skipped will be available in $PATH.
"""

import subprocess
import logging
import os.path as op
import time
import os
import sys

from pbcommand.pb_io import load_tool_contract_from

DIR_NAME = op.join(op.dirname(__file__), "registered-tool-contracts")
SKIP_NS = set(["pbinternal2", "pbscala"])

def run(argv=()):
    if "--help" in argv:
        print __doc__
        return 0
    logging.basicConfig(level=logging.INFO)
    t_start = time.time()
    for file_name in os.listdir(DIR_NAME):
        tc_file = op.join(DIR_NAME, file_name)
        tc = load_tool_contract_from(tc_file)
        if tc.task.task_id.split(".")[0] in SKIP_NS:
            logging.warn("Skipping %s", file_name)
            continue
        exe = tc.driver.driver_exe.strip().split()
        cmd = list(exe[:-1])
        if exe[-1] == "--resolved-tool-contract":
            cmd.append("--emit-tool-contract")
        elif exe[-1] == "run-rtc":
            cmd.extend(["emit-tool-contract", tc.task.task_id])
        else:
            logging.warn("Don't know how to translate command '%s'",
                         tc.driver.driver_exe)
            continue
        logging.info("Running command '%s'", " ".join(cmd))
        json_str = subprocess.check_output(cmd)
        with open(tc_file, "w") as json_out:
            json_out.write(json_str)
    t_end = time.time()
    logging.info("Tool contracts processed in %.0fs", t_end-t_start)
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv))
