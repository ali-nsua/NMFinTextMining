import numpy as np
from math import sqrt
from sklearn.decomposition import NMF
from scipy.sparse.linalg import svds
from sklearn.utils.extmath import svd_flip, squared_norm


"""
The superclass NMF, the norm and the init_nmf functions were obtained from
the Scikit-Learn open-source Python library.

Copyright 2020 Scikit-Learn

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""


class SparseNMF(NMF):
    """
    Performs exactly the same as Scikit-Learn's NMF, with the `init` parameter fixed to a variant of `nndsvd`
    which was implemented to use scipy's sparse svd instead of the regular.
    """
    def __init__(self, n_components=None, solver='cd',
                 beta_loss='frobenius', tol=1e-4, max_iter=200,
                 random_state=None, alpha=0., l1_ratio=0., verbose=0,
                 shuffle=False):
        super(SparseNMF, self).__init__(n_components=n_components, init='custom',
                                        solver=solver, beta_loss=beta_loss, tol=tol,
                                        max_iter=max_iter, random_state=random_state,
                                        alpha=alpha, l1_ratio=l1_ratio, verbose=verbose,
                                        shuffle=shuffle)

    def fit_transform(self, X, y=None, W=None, H=None):
        """Learn a NMF model for the data X and returns the transformed data.

        This is more efficient than calling fit followed by transform.

        Parameters
        ----------
        X : {array-like, sparse matrix}, shape (n_samples, n_features)
            Data matrix to be decomposed

        y : Ignored

        W : array-like, shape (n_samples, n_components)
            If init='custom', it is used as initial guess for the solution.

        H : array-like, shape (n_components, n_features)
            If init='custom', it is used as initial guess for the solution.

        Returns
        -------
        W : array, shape (n_samples, n_components)
            Transformed data.
        """
        W, H = init_nmf(X, self.n_components)
        return super(SparseNMF, self).fit_transform(X, W=W, H=H)

    def fit(self, X, y=None, **params):
        """Learn a NMF model for the data X.

        Parameters
        ----------
        X : {array-like, sparse matrix}, shape (n_samples, n_features)
            Data matrix to be decomposed

        y : Ignored

        Returns
        -------
        self
        """
        self.fit_transform(X, **params)
        return self


def norm(x):
    """Dot product-based Euclidean norm implementation

    See: http://fseoane.net/blog/2011/computing-the-vector-norm/

    Parameters
    ----------
    x : array-like
        Vector for which to compute the norm
    """
    return sqrt(squared_norm(x))


def init_nmf(X, n_components, eps=1e-6):
    """
    Initialize NMF using Sparse SVD

    Parameters
    ----------
    X            : array-like
                   Vector for which to compute the norm

    n_components : int
                   Number of components

    eps          : float
                   Epsilon parameter

    Returns
    -------
    W : array-like
    H : array-like

    """
    U, S, V = svds(X, n_components)
    S = S[::-1]
    U, V = svd_flip(U[:, ::-1], V[::-1])
    W, H = np.zeros(U.shape), np.zeros(V.shape)

    # The leading singular triplet is non-negative
    # so it can be used as is for initialization.
    W[:, 0] = np.sqrt(S[0]) * np.abs(U[:, 0])
    H[0, :] = np.sqrt(S[0]) * np.abs(V[0, :])

    for j in range(1, n_components):
        x, y = U[:, j], V[j, :]

        # extract positive and negative parts of column vectors
        x_p, y_p = np.maximum(x, 0), np.maximum(y, 0)
        x_n, y_n = np.abs(np.minimum(x, 0)), np.abs(np.minimum(y, 0))

        # and their norms
        x_p_nrm, y_p_nrm = norm(x_p), norm(y_p)
        x_n_nrm, y_n_nrm = norm(x_n), norm(y_n)

        m_p, m_n = x_p_nrm * y_p_nrm, x_n_nrm * y_n_nrm

        # choose update
        if m_p > m_n:
            u = x_p / x_p_nrm
            v = y_p / y_p_nrm
            sigma = m_p
        else:
            u = x_n / x_n_nrm
            v = y_n / y_n_nrm
            sigma = m_n

        lbd = np.sqrt(S[j] * sigma)
        W[:, j] = lbd * u
        H[j, :] = lbd * v

    W[W < eps] = 0
    H[H < eps] = 0

    return W, H
