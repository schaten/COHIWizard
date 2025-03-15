"""Calculation of a TX coil for MW near field coupling with ferrite antennas
Sources: Loop inductance: https://en.wikipedia.org/wiki/Inductance
magnetic field of a loop: https://www.emworks.com/application/calculating-magnetic-field-on-the-axis-of-a-current-loop

"""

import numpy as np
import matplotlib.pyplot as plt

# Constants
mu0 = 4*np.pi*1e-7  # Vacuum permeability
#f = np.linspace(200e3,2e6,10)  # Frequency range
f = 1e6  # Frequency
w = 2*np.pi*f  # Angular frequency
I = 1  # Current in the loop
R = 0.2  # Loop radius
d = 0.005  # wire diameter
z = np.linspace(0.01,1,10)  # Distance from the loop
N = 1  # Number of turns
A = np.pi*R**2  # Area of the loop
V = 5 # Voltage at loop terminals

L = (N ** 2) * mu0 * R * (np.log(8*R/d) - 2)  # Loop inductance
print(f"Loop inductance: {L*1e6:.2f} uH")

I = V/w/L
print(f"Current in the loop: {I:.2f} A")

B = mu0 * N * I * R**2 / (2 * (R**2 + z**2)**(3/2))  # Magnetic field of a loop

plt.plot(z,B)
plt.xlabel('Distance from loop [m]')
plt.ylabel('Magnetic field [T]')
plt.show()
