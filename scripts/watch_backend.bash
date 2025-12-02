#!/bin/bash
#
## @file scripts/watch_backend.bash
## @author Victor Mercola
## @date 2025-11-30
## @brief View `slopspotter-cli`'s log as it updates on Linux
watch -n 2 tail --lines=20 slopspotter-cli/log.log