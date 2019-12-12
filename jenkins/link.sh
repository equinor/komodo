#!/bin/bash

set -e

if [[ -z "${KOMODO_TARGET_ROOT// }" ]]; then
    echo "Missing KOMODO_TARGET_ROOT"
    exit 1
fi

if [[ -z "${KOMODO_LINK_ROOT// }" ]]; then
    echo "Missing KOMODO_LINK_ROOT"
    exit 1
fi

if [[ -z "${LINK_NAME// }" ]]; then
    echo "Missing LINK_NAME"
    exit 1
fi

if [[ -z "${TARGET_VERSION// }" ]]; then
    echo "Missing TARGET_VERSION"
    exit 1
fi

TARGET=${KOMODO_TARGET_ROOT}/${TARGET_VERSION}
LINK=${KOMODO_LINK_ROOT}/${LINK_NAME}

if [[ -f ${LINK} ]]; then
   CURRENT_LINK=$(readlink ${LINK})
   echo "Current: ${LINK} -> ${CURRENT_LINK}"
fi

if [[ "${CURRENT_LINK}" != "${TARGET}" ]]; then
      if [[ -d "${TARGET}" ]]; then
          echo "Linking ${LINK} -> ${TARGET}"
          rm -f ${LINK}
          ln -s ${TARGET} ${LINK}
      else
          echo "Version ${TARGET} not found"
          exit 1;
      fi
fi
