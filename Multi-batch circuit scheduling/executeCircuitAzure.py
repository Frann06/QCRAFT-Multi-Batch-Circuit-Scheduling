#!/usr/bin/env python
# coding: utf-8

# -----------------------------
# Imports
# -----------------------------
from qiskit import transpile
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import qiskit
import numpy as np
import re
import threading
import json
import os

from qiskit.circuit.library import MCXGate
from azure.quantum.qiskit import AzureQuantumProvider


# ==========================================================
# Execute Circuit on Azure Quantum (Qiskit)
# ==========================================================
class executeCircuitAzure:

    def __init__(self):
        self.transpile_lock = threading.Lock()
        self.condition = threading.Condition()
        self.queued_jobs = 0

        # Azure Quantum provider
        self.provider = AzureQuantumProvider(
            resource_id = "/subscriptions/1a8522b9-740f-42f3-be08-cc9a3c576030/resourceGroups/AzureQuantum/providers/Microsoft.Quantum/Workspaces/azurescheduler2026",
            location = "eastus"
        )

    # --------------------------------------------------
    # Obtain backend
    # --------------------------------------------------
    def obtain_machine(self, machine: str) -> qiskit.providers.BackendV2:
        return self.provider.get_backend(machine)

    # --------------------------------------------------
    # Inverse parser: string -> QuantumCircuit
    # (COPIA EXACTA del de IBM)
    # --------------------------------------------------
    def code_to_circuit_azure(self, code_str: str) -> QuantumCircuit:
        try:
            lines = code_str.strip().split('\n')
            qreg = creg = circuit = None

            for line in lines:
                if 'import' not in line:
                    if "QuantumRegister" in line:
                        qreg_name = line.split('=')[0].strip()
                        num_qubits = int(line.split('(')[1].split(')')[0].split(',')[0].strip())
                        qreg = qiskit.QuantumRegister(num_qubits, qreg_name)

                    elif "ClassicalRegister" in line:
                        creg_name = line.split('=')[0].strip()
                        num_clbits = int(line.split('(')[1].split(')')[0].split(',')[0].strip())
                        creg = qiskit.ClassicalRegister(num_clbits, creg_name)

                    elif "QuantumCircuit" in line:
                        circuit = qiskit.QuantumCircuit(qreg, creg)

                    elif "circuit." in line:
                        if ".c_if(" in line:
                            operation, condition = line.split('.c_if(')
                        else:
                            operation = line
                            condition = None

                        gate_name = operation.split('circuit.')[1].split('(')[0]
                        args = re.split(r'\s*,\s*', operation.split('(', 1)[1].rsplit(')', 1)[0].strip())

                        if gate_name == "measure":
                            qubit = qreg[int(args[0].split('[')[1].strip(']').split('+')[0]) +
                                         int(args[0].split('[')[1].strip(']').split('+')[1].strip(') '))
                                         if '+' in args[0]
                                         else int(args[0].split('[')[1].strip(']'))]
                            cbit = creg[int(args[1].split('[')[1].strip(']').split('+')[0]) +
                                        int(args[1].split('[')[1].strip(']').split('+')[1].strip(') '))
                                        if '+' in args[1]
                                        else int(args[1].split('[')[1].strip(']'))]
                            circuit.measure(qubit, cbit)

                        elif gate_name == "barrier":
                            if args[0] == '':
                                circuit.barrier()
                            elif args[0] == qreg.name:
                                circuit.barrier(*qreg)
                            else:
                                qubits = [qreg[int(arg.split('[')[1].strip(']').split('+')[0]) +
                                               int(arg.split('[')[1].strip(']').split('+')[1].strip(') '))
                                               if '+' in arg
                                               else int(arg.split('[')[1].strip(']'))]
                                          for arg in args if '[' in arg]
                                circuit.barrier(qubits)

                        elif gate_name == "append":
                            gate_type = args[0]
                            qubits = [qreg[int(re.search(r'\[(\d+)\]', arg).group(1))]
                                      for arg in args[1:] if '[' in arg]
                            control_qubits = qubits[:-1]
                            target_qubit = qubits[-1]

                            if gate_type == 'mc_x_gate':
                                mcx = MCXGate(len(control_qubits))
                                circuit.append(mcx, control_qubits + [target_qubit])

                            elif gate_type == 'mc_y_gate':
                                circuit.sdg(target_qubit)
                                mcx = MCXGate(len(control_qubits))
                                circuit.append(mcx, control_qubits + [target_qubit])
                                circuit.s(target_qubit)

                            elif gate_type == 'mc_z_gate':
                                circuit.h(target_qubit)
                                mcx = MCXGate(len(control_qubits))
                                circuit.append(mcx, control_qubits + [target_qubit])
                                circuit.h(target_qubit)

                        else:
                            qubits = [qreg[int(arg.split('[')[1].strip(']').split('+')[0]) +
                                           int(arg.split('[')[1].strip(']').split('+')[1].strip(') '))
                                           if '+' in arg
                                           else int(arg.split('[')[1].strip(']'))]
                                      for arg in args if '[' in arg]

                            params = [eval(arg, {"__builtins__": None, "np": np}, {})
                                      for param_str in args if '[' not in param_str
                                      for arg in param_str.split(',')]

                            gate_op = getattr(circuit, gate_name)(*params, *qubits) if params \
                                      else getattr(circuit, gate_name)(*qubits)

                            if condition:
                                creg_name, val = condition.split(')')[0].split(',')
                                gate_op.c_if(creg, int(val.strip()))

        except Exception:
            raise ValueError("Invalid circuit code")

        return circuit

    # --------------------------------------------------
    # Transpiled circuit depth
    # --------------------------------------------------
    def get_transpiled_circuit_depth_azure(
        self,
        circuit: QuantumCircuit,
        backend: qiskit.providers.BackendV2
    ) -> int:
        with self.transpile_lock:
            qc_basis = transpile(circuit, backend=backend)
        return qc_basis.depth()

    # --------------------------------------------------
    # Run circuit (Azure)
    # --------------------------------------------------
    def runAzure(self, machine: str, circuit: QuantumCircuit, shots: int) -> dict:

        if machine == "local":
            backend = AerSimulator()
            job = backend.run(circuit, shots=int(shots))
            return job.result().get_counts()

        backend = self.obtain_machine(machine)

        with self.transpile_lock:
            qc_basis = transpile(circuit, backend=backend)

        while True:
            with self.condition:
                if self.queued_jobs < 3:
                    self.queued_jobs += 1
                    break
                else:
                    self.condition.wait()

        job = backend.run(qc_basis, shots=int(shots))
        result = job.result()
        counts = result.get_counts()

        with self.condition:
            self.queued_jobs -= 1
            self.condition.notify()

        return counts

    # --------------------------------------------------
    # Run + save job id (Azure)
    # --------------------------------------------------
    def runAzure_save(
        self,
        machine: str,
        circuit: QuantumCircuit,
        shots: int,
        users: list,
        qubit_number: list,
        circuit_names: list
    ) -> dict:

        backend = self.obtain_machine(machine)

        with self.transpile_lock:
            qc_basis = transpile(circuit, backend=backend)

        while True:
            with self.condition:
                if self.queued_jobs < 3:
                    self.queued_jobs += 1
                    break
                else:
                    self.condition.wait()

        job = backend.run(qc_basis, shots=int(shots))
        job_id = job.id()
        provider = "azure"
        user_shots = [shots] * len(circuit_names)

        script_dir = os.path.dirname(os.path.realpath(__file__))
        ids_file = os.path.join(script_dir, 'ids.txt')

        with open(ids_file, 'a') as f:
            f.write(json.dumps({
                job_id: (users, qubit_number, user_shots, provider, circuit_names)
            }))
            f.write('\n')

        result = job.result()
        counts = result.get_counts()

        with self.condition:
            self.queued_jobs -= 1
            self.condition.notify()

        # Remove ID from file
        with open(ids_file, 'r') as f:
            lines = f.readlines()
        with open(ids_file, 'w') as f:
            for line in lines:
                if job_id not in line:
                    f.write(line)

        return counts

    # --------------------------------------------------
    # List Azure devices
    # --------------------------------------------------
    def Azure(self) -> list:
        devices_info = []

        for backend in self.provider.backends():
            config = backend.configuration()
            status = backend.status()

            if "simulator" in backend.name():
                continue

            devices_info.append({
                "deviceName": backend.name(),
                "queueSize": None,
                "deviceStatus": "ONLINE" if status.operational else "OFFLINE",
                "deviceType": "QPU",
                "providerName": "AZURE",
                "qubitCount": config.n_qubits,
            })

        return devices_info
