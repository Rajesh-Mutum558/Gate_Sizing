import numpy as np
from math import ceil, floor
from collections import defaultdict
from gpkit import Variable, Model, VectorVariable
import sys
import math
from google.colab import files

sys.setrecursionlimit(10000)


class Gate:
    def __init__(self, name, gate_type, num_inputs,g_value, gate_size):
        self.name = name
        self.gate_type = gate_type
        self.num_inputs = num_inputs
        self.gate_size = gate_size
        self.fanout_gates = []
        self.delay = None
        self.delay_paths = 0
        self.input = []
        self.g_value = g_value
        self.delay_value = 0
        self.gate_size_value = 0
        self.delay_r = 1000
        self.gate_rounded = 0


    def calculate_delay(self):

        p = self.num_inputs

        if len(self.fanout_gates) == 0:
            h = (100 / (self.gate_size))
        else:
            fanout_g_values = []
            for fanout_gate in self.fanout_gates:
                fanout_g_values.append(
                    fanout_gate.gate_size * fanout_gate.g_value)

            h = (sum(fanout_g_values) / self.gate_size )

        self.delay = h + p


    def calculate_delay_paths(self, constraints):

            if (len(self.input) == 1):
                input_gate = self.input[0]
                self.delay_paths = (input_gate.delay_paths + self.delay)

            elif len(self.input) > 1:
                max_input_delay = Variable(f"{self.name}")
                for input_gate in self.input:
                    constraints.append(max_input_delay >= (input_gate.delay_paths + self.delay))
                self.delay_paths = max_input_delay

            else:
                self.delay_paths = self.delay


def gate_size_final(dag,topological_order):
  m = 0
  for gate_name in reversed(topological_order):
      gate = dag.nodes[gate_name]
      p = gate.num_inputs

      if len(gate.fanout_gates) == 0:
            h = (100 / (gate.gate_size_value))
            gate.delay_r = 0;
      else:
          fanout_g_values = []
          for fanout_gate in gate.fanout_gates:
                fanout_g_values.append(
                    fanout_gate.gate_size_value * fanout_gate.g_value)

          h = (sum(fanout_g_values) / gate.gate_size_value )

      new_value = h + p
      gate.delay_value = gate.delay_value + gate.delay_r
      while int(new_value * (10**15)) > int((gate.delay_value) * (10**15)):
            gate.gate_size_value += 1
            p = gate.num_inputs

            if len(gate.fanout_gates) == 0:
                h = (100 / gate.gate_size_value)
            else:
                fanout_g_values = []
                for fanout_gate in gate.fanout_gates:
                    fanout_g_values.append(fanout_gate.gate_size_value * fanout_gate.g_value)

                h = (sum(fanout_g_values) / gate.gate_size_value)

            new_value = h + p

      if gate.gate_size_value > gate.gate_rounded:
          a = floor((gate.gate_size_value - gate.gate_rounded) / 3)
          if (gate.gate_size_value - gate.gate_rounded) == 2:
              m += 1;
              #print("m value",m)
          if m == 3:
              gate.gate_size_value -= 1
              m = 0
          #print('a value ', a)
          gate.gate_size_value -= a

      for input_gate in gate.input:
          if (gate.delay_value - new_value) < input_gate.delay_r :
              input_gate.delay_r = gate.delay_value - new_value



def calculate_delay_value(dag):
  for gate_name, gate in dag.nodes.items():
      p = gate.num_inputs

      if len(gate.fanout_gates) == 0:
            h = (100 / (gate.gate_size_value))
      else:
          fanout_g_values = []
          for fanout_gate in gate.fanout_gates:
                fanout_g_values.append(
                    fanout_gate.gate_size_value * fanout_gate.g_value)

          h = (sum(fanout_g_values) / gate.gate_size_value )

      gate.delay_value = h + p
      #print('delay value', gate.delay_value)


def find_longest_paths(dag,topological_order):
    distances = {gate_name: 0 for gate_name in topological_order}
    predecessors = {gate_name: None for gate_name in topological_order}

    for gate_name, gate in dag.nodes.items():
        for neighbor in gate.fanout_gates:
            new_distance = distances[gate_name] + 1
            if new_distance > distances[neighbor.name]:
                distances[neighbor.name] = new_distance
                predecessors[neighbor.name] = gate_name

    max_distance = max(distances.values())

    longest_paths = []
    for node, distance in distances.items():
        if distance == max_distance:
            current_path = []
            current_node = node
            while current_node is not None:
                current_path.insert(0, current_node)
                current_node = predecessors[current_node]
            longest_paths.append(current_path)

    print(f"All Longest Paths (Length: {max_distance}):")
    for path in longest_paths:
        print(path)


class DAG:
    def __init__(self):
        self.nodes = {}

    def topological_sort(self):
        topological_order = []
        successors_list = set()

        # Find nodes with no incoming edges (input is an empty list)
        for gate_name, gate in self.nodes.items():
            if not gate.input:
                topological_order.append(gate_name)
                successors_list.update(a.name for a in gate.fanout_gates)

        successors_list = list(successors_list)

        while successors_list:
            gate_name = successors_list.pop(0)
            gate = self.nodes[gate_name]
            if  all(pred.name in topological_order for pred in gate.input):
              topological_order.append(gate_name)
              if gate.fanout_gates:
                  successors_list.extend([b.name for b in gate.fanout_gates if b.name not in successors_list])

        return topological_order

    def add_gate(self, name, gate_type, num_inputs, g_value, gate_size):
        gate = Gate(name, gate_type, num_inputs, g_value, gate_size)
        self.nodes[name] = gate

    def add_connection_input(self, source_gate_name, destination_gate_name):
        if source_gate_name in self.nodes and destination_gate_name in self.nodes:
            self.nodes[source_gate_name].input.append(self.nodes[destination_gate_name])

    def add_connection_fanout(self, source_gate_name, destination_gate_name):
        if source_gate_name in self.nodes and destination_gate_name in self.nodes:
            self.nodes[source_gate_name].fanout_gates.append(self.nodes[destination_gate_name])

    def calculate_delays(self):
        for gate_name, gate in self.nodes.items():
            gate.calculate_delay()

    def calculate_delay_path(self,name,topological_order):
        for gate_name in topological_order:
            gate = self.nodes[gate_name]
            gate.calculate_delay_paths(name)

def parse_verilog(filename):
    netlist = defaultdict(list)

    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith('//') or line.startswith('/*'):
                continue
            if line.startswith('module') or line.startswith('endmodule') or line == '':
                continue
            if line.startswith('input') or line.startswith('output'):
                continue
            if line.startswith('wire'):
                continue
            if '(' not in line:  # Skip lines without an opening parenthesis
                continue

            parts = line.split('(')
            gate_info = parts[0].split(' ')
            if len(gate_info) < 2:
                continue  # Skip lines that don't have the expected gate information

            gate_type = gate_info[0].strip()
            gate_name = gate_info[1].strip()

            input_names = []
            output_name = ''
            if len(parts) > 1:
                inputs = parts[1].rstrip(');').split(',')
                output_name = inputs.pop(0).strip()
                input_names = [name.strip() for name in inputs]

            if gate_type == 'not':
                g_value = 1
            elif gate_type == 'nand':
                g_value = (len(input_names) + 2) / 3
            elif gate_type == 'nor':
                g_value = (2 * len(input_names) + 1) / 3
            else:
                g_value = 1  # Default value when gate type is not recognized

            netlist[gate_name] = {'type': gate_type,
                'inputs': input_names,
                'output': output_name,
                'g_value': g_value}

    return netlist

uploaded = files.upload()
filename = list(uploaded.keys())[0]
file_location =r'C:\Users\mutum\Downloads\c17.v'
netlist = parse_verilog(filename)
dag = DAG()
all_gate_size = VectorVariable(len(netlist),"x")
i = 0
for gate_name, gate_info in netlist.items():
    gate_type = gate_info['type']
    inputs = gate_info['inputs']
    output = gate_info['output']
    g_value = gate_info['g_value']
    gate_size = all_gate_size[i]
    i += 1

    dag.add_gate(gate_name, gate_type, len(inputs), g_value, gate_size)

for output_gate, gate_info in netlist.items():
    input_names = gate_info['inputs']
    output_name = gate_info['output']
    for gate_name, gate_info2 in netlist.items():
        if gate_name != output_gate and gate_info2['output'] in input_names:
            dag.add_connection_input(output_gate, gate_name)
        if gate_name != output_gate and output_name in gate_info2['inputs']:
            dag.add_connection_fanout(output_gate, gate_name)


# Create variables for constraints
T0 = Variable("T0")

topological_order = dag.topological_sort()
print(topological_order)
constant=[]
dag.calculate_delays()
dag.calculate_delay_path(constant,topological_order)

# Create constraints
constraints = []
constraints += constant

# Find gates with no fanout based on the 'fanout' attribute
gates_with_no_fanout = [gate for name,gate in dag.nodes.items() if len(gate.fanout_gates) == 0]

# Add the delay_paths constraint for gates with no fanout
for gate in gates_with_no_fanout:
    constraints.append(gate.delay_paths <= T0)

# Add gate size constraints (optional if already initialized)
for gate_size in all_gate_size:
    constraints.append(gate_size >= 1)
    constraints.append(gate_size <= 100)

upper = 1.1*152.49563916511295
print('t_min',upper)
# #constraints.append(all_gate_size[0]==2)
constraints.append(T0<=upper)
objective = all_gate_size.sum()

#objective = T0

m = Model(objective, constraints)
sol1 = m.solve(verbosity=1)
gate_sizesz = list(sol1["variables"]["x"])
print(sol1['cost'])
#print(gate_sizesz)
print(constraints.pop())

# t_spec=161
upper = 1.071545*152.49563916511295
# #constraints.append(all_gate_size[0]==2)
constraints.append(T0<=upper)
objective = all_gate_size.sum()

#objective = T0

m = Model(objective, constraints)
sol2 = m.solve(verbosity=1)
print(constraints.pop())

t_wall = sol2["variables"]["T0"]
print("t_wall", t_wall)

gate_sizes = list(sol2["variables"]["x"])
print(gate_sizes)
gate_rounded = [round(gate) for gate in gate_sizesz]
#print(gate_rounded)

for i, (gate_name, gate) in enumerate(dag.nodes.items()):
    gate.gate_size_value = gate_sizes[i]
    gate.gate_rounded = gate_rounded[i]

calculate_delay_value(dag)

upper = 1.3*152.49563916511295
# #constraints.append(all_gate_size[0]==2)
constraints.append(T0<=upper)
objective = all_gate_size.sum()

#objective = T0

m = Model(objective, constraints)
sol3 = m.solve(verbosity=1)

gate_sizess = list(sol3["variables"]["x"])

gate_sizes_rounded = [round(gate) for gate in gate_sizess]
#print(gate_sizes_rounded)
for i, (gate_name, gate) in enumerate(dag.nodes.items()):
    gate.gate_size_value = gate_sizes_rounded[i]

gate_size_final(dag,topological_order)
print('[', end = '')
new_gate = []
for gate_name, gate in dag.nodes.items():
    new_gate.append(gate.gate_size_value)
    print(gate.gate_size_value,end = ', ')
print(']')

