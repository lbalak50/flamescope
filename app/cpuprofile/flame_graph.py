# This file is part of FlameScope, a performance analysis tool created by the
# Netflix cloud performance team. See:
#
#    https://github.com/Netflix/flamescope
#
# Copyright 2018 Netflix, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import json
import math
from app.common.fileutil import get_file
from app.common.flame_graph import generate_flame_graph
from app.cpuprofile.chrome import get_cpuprofiles
from app import nflxprofile_pb2


def parse_nodes(data):
    profile = nflxprofile_pb2.Profile()
    profile.nodes[0].function_name = 'fakenode'
    profile.nodes[0].hit_count = 0
    for node in data['nodes']:
        node_id = node['id']
        function_name = node['callFrame']['functionName']
        children = node.get('children', None)
        hit_count = node.get('hitCount', 0)
        profile.nodes[node_id].function_name = function_name
        profile.nodes[node_id].hit_count = hit_count
        profile.nodes[node_id].libtype = ''
        if children:
            for child_id in children:
                profile.nodes[node_id].children.append(child_id)
    return profile.nodes


def get_meta_ids(nodes):
    program_node_id = None
    idle_node_id = None
    gc_node_id = None
    for key, node in nodes.items():
        if node.function_name == '(program)':
            program_node_id = key
        elif node.function_name == '(idle)':
            idle_node_id = key
        elif node.function_name == '(garbage collector)':
            gc_node_id = key
    return program_node_id, idle_node_id, gc_node_id


def cpuprofile_generate_flame_graph(file_path, range_start, range_end):
    f = get_file(file_path)
    chrome_profile = json.load(f)
    f.close()

    cpuprofiles = get_cpuprofiles(chrome_profile)

    # a chrome profile can contain multiple cpu profiles
    # using only the first one for now
    # TODO: add support for multiple cpu profiles
    profile = cpuprofiles[0]

    root_id = profile['nodes'][0]['id']
    nodes = parse_nodes(profile)
    ignore_ids = get_meta_ids(nodes)
    start_time = profile['startTime']
    if range_start is not None:
        adjusted_range_start = (math.floor(start_time / 1000000) + range_start) * 1000000
    if range_end is not None:
        adjusted_range_end = (math.floor(start_time / 1000000) + range_end) * 1000000

    return generate_flame_graph(nodes, root_id, profile['samples'], profile['timeDeltas'], profile['startTime'], adjusted_range_start, adjusted_range_end, ignore_ids)
