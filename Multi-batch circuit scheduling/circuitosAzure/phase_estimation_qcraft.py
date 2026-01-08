from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
import numpy as np

from azure.quantum.qiskit import AzureQuantumProvider

# =============================
# Circuito (SIN CAMBIOS)
# =============================
qreg_q = QuantumRegister(4, 'q')
creg_c = ClassicalRegister(4, 'c')
circuit = QuantumCircuit(qreg_q, creg_c)

circuit.h(qreg_q[0])
circuit.h(qreg_q[1])
circuit.h(qreg_q[2])
circuit.x(qreg_q[3])

circuit.cp(np.pi / 4, qreg_q[0], qreg_q[3])
circuit.cp(np.pi / 4, qreg_q[1], qreg_q[3])
circuit.cp(np.pi / 4, qreg_q[1], qreg_q[3])
circuit.cp(np.pi / 4, qreg_q[2], qreg_q[3])
circuit.cp(np.pi / 4, qreg_q[2], qreg_q[3])
circuit.cp(np.pi / 4, qreg_q[2], qreg_q[3])
circuit.cp(np.pi / 4, qreg_q[2], qreg_q[3])

circuit.barrier()

circuit.swap(qreg_q[0], qreg_q[2])
circuit.h(qreg_q[0])
circuit.cp(-np.pi / 2, qreg_q[0], qreg_q[1])
circuit.h(qreg_q[1])
circuit.cp(-np.pi / 4, qreg_q[0], qreg_q[2])
circuit.cp(-np.pi / 2, qreg_q[1], qreg_q[2])
circuit.h(qreg_q[2])

circuit.barrier()

circuit.measure(qreg_q[0], creg_c[0])
circuit.measure(qreg_q[1], creg_c[1])
circuit.measure(qreg_q[2], creg_c[2])

# =============================
# Ejecución en Azure (estilo IBM)
# =============================
shots = 100

provider = AzureQuantumProvider()
backend = provider.get_backend("rigetti.sim.qvm") # Rigetti Simulator

qc_basis = transpile(circuit, backend)
job = backend.run(qc_basis, shots=shots)
job_result = job.result()

print(job_result.get_counts())






# =============================
# OTRA OPCION SI LO DE ARRIBA NO VA:
# =============================

# from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
# from qiskit import transpile
# from azure.quantum.qiskit import AzureQuantumProvider
# import numpy as np

# # 1. Configuración del Provider (Sin tokens visibles, igual que haces con IBM)
# # Azure buscará automáticamente las credenciales guardadas en tu sistema (az login)
# provider = AzureQuantumProvider()

# # 2. Definición del Circuito (Idéntico al tuyo)
# qreg_q = QuantumRegister(4, 'q')
# creg_c = ClassicalRegister(4, 'c')
# circuit = QuantumCircuit(qreg_q, creg_c)

# circuit.h(qreg_q[0])
# circuit.h(qreg_q[1])
# circuit.h(qreg_q[2])
# circuit.x(qreg_q[3])
# circuit.cp(np.pi / 4, qreg_q[0], qreg_q[3])
# circuit.cp(np.pi / 4, qreg_q[1], qreg_q[3])
# circuit.cp(np.pi / 4, qreg_q[1], qreg_q[3])
# circuit.cp(np.pi / 4, qreg_q[2], qreg_q[3])
# circuit.cp(np.pi / 4, qreg_q[2], qreg_q[3])
# circuit.cp(np.pi / 4, qreg_q[2], qreg_q[3])
# circuit.cp(np.pi / 4, qreg_q[2], qreg_q[3])
# circuit.barrier(qreg_q[0], qreg_q[1], qreg_q[2], qreg_q[3])
# circuit.swap(qreg_q[0], qreg_q[2])
# circuit.h(qreg_q[0])
# circuit.cp(-np.pi / 2, qreg_q[0], qreg_q[1])
# circuit.h(qreg_q[1])
# circuit.cp(-np.pi / 4, qreg_q[0], qreg_q[2])
# circuit.cp(-np.pi / 2, qreg_q[1], qreg_q[2])
# circuit.h(qreg_q[2])
# circuit.barrier(qreg_q[0], qreg_q[1], qreg_q[2], qreg_q[3])
# circuit.measure(qreg_q[0], creg_c[0])
# circuit.measure(qreg_q[2], creg_c[2])
# circuit.measure(qreg_q[1], creg_c[1])

# # 3. Parámetros y Backend
# shots = 10000

# # En Azure, en lugar de Aer, usamos un simulador de partner disponible en tu Workspace
# # Ejemplo usando el simulador de IonQ:
# backend = provider.get_backend("ionq.simulator")

# # 4. Transpilación y Ejecución (Estructura igual a la tuya)
# qc_basis = transpile(circuit, backend)
# job = backend.run(qc_basis, shots=shots) # En Azure usamos backend.run en lugar de execute

# # 5. Resultados
# job_result = job.result()
# print(job_result.get_counts(qc_basis))