
import os.path as op
import os
import sys

from pbsmrtpipe.pb_io import write_pipeline_templates_to_json
from pbsmrtpipe.loader import load_all_installed_pipelines, load_all_tool_contracts

import pb_pipelines_sa3
import pb_pipelines_falcon


def main(argv):
    base_path = op.dirname(__file__)
    dest_path = op.join(base_path, "resolved-pipeline-templates")
    os.environ["PB_TOOL_CONTRACT_DIR"] = op.join(base_path, "registered-tool-contracts")
    rtasks_d = load_all_tool_contracts()
    pts = load_all_installed_pipelines()
    write_pipeline_templates_to_json(pts.values(), rtasks_d, dest_path)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
