"""Demo of positional / time encoding"""

import numpy as np

class PosEncode:
    """From the "Attention is all you need" article"""
    def __init__(self, dim):
        self.dim = dim

    def __call__(self, x):
        pos_vector = np.array([x / np.power(10000, 2 * (i // 2) / self.dim) for i in range(self.dim)])

        pos_vector[0::2] = np.sin(pos_vector[0::2])  # apply sin on 0th,2nd,4th...dim
        pos_vector[1::2] = np.cos(pos_vector[1::2])  # apply cos on 1st,3rd,5th...dim

        return pos_vector

class PeriodicTimeEncode:
    """Time encoding designed to be periodic"""

    def __init__(self, max_period, dim, period_reduction=4):
        self.max_period = max_period
        self.dim = dim
        self.period_reduction = period_reduction

    def __call__(self, x):
        c = 2 * np.pi / self.max_period
        a = self.period_reduction # Reduction of period by a forth
        pos_vector = np.array([ c * x * a**(i//2) for i in range(self.dim)])

        pos_vector[0::2] = np.sin(pos_vector[0::2])  # apply sin on 0th,2nd,4th...dim
        pos_vector[1::2] = np.cos(pos_vector[1::2])  # apply cos on 1st,3rd,5th...dim

        return pos_vector

def main():
    from matplotlib import pyplot as plt

    pos_encoder = PeriodicTimeEncode(365, 6)

    X = range(365)
    Y = np.concatenate([np.expand_dims(pos_encoder(x), axis=1) for x in X], axis=1)
    for i in range(Y.shape[0]):
        plt.plot(X, Y[i,:])
    plt.show()

if __name__ == '__main__':
    main()