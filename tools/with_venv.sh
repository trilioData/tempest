#!/bin/bash
TOOLS_PATH=${TOOLS_PATH:-$(dirname $0)/../}
VENV_PATH=${VENV_PATH:-${TOOLS_PATH}}
VENV_DIR=${VENV_DIR:-/.venv}
VENV=${VENV:-${VENV_PATH}/${VENV_DIR}}
OPENSTACK_DISTRO=MOSK
if [[ ${OPENSTACK_DISTRO,,} == 'mosk' ]]
then
    source ${VENV}/bin/activate && cd /root && eval "$(<env.sh)" && cd - && "$@"
else
    source ${VENV}/bin/activate && "$@"
fi
