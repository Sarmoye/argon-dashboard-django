import numpy as np
import matplotlib.pyplot as plt

# Paramètres
alpha = 0.5
Sarmoye0 = 1

# Intervalle de temps
t = np.linspace(0, 10, 200)
Sarmoye = Sarmoye0 * np.exp(alpha * t)

# Tracé de la courbe
plt.plot(t, Sarmoye, label=r'$Sarmoye(t)=Sarmoye_0\,e^{\alpha t}$')
plt.xlabel('Temps t')
plt.ylabel('Sarmoye(t)')
plt.title("Evolution exponentielle de Sarmoye")
plt.legend()
plt.grid(True)
plt.show()
