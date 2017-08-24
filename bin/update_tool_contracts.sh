#!/bin/bash
#
# Utility script to update (nearly) all tool contracts from smrttools build

set -o errexit
set -o pipefail
set -o nounset
set -o xtrace

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT_DIR=$(readlink -f "${__dir}/..")

cd $BUNDLE_ROOT_DIR
source /mnt/software/Modules/current/init/bash
module load smrttools/mainline

make tool-contracts
