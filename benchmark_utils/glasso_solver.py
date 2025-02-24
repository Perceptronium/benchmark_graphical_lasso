from benchopt.utils import safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np
    from numpy.linalg import norm

    from sklearn.utils.validation import check_random_state
    from sklearn.linear_model import _cd_fast as cd_fast

    from numba import njit
    import scipy

    from skglm.solvers import AndersonCD
    from skglm.datafits import QuadraticHessian
    from skglm.penalties import WeightedL1
    from skglm.utils.jit_compilation import compiled_clone


class GraphicalLasso():
    def __init__(self,
                 alpha=1.,
                 weights=None,
                 algo="dual",
                 inner_anderson=False,
                 outer_anderson=False,
                 max_iter=100,
                 tol=1e-8,
                 warm_start=False,
                 inner_tol=1e-4,
                 ):
        self.alpha = alpha
        self.weights = weights
        self.algo = algo
        self.inner_anderson = inner_anderson
        self.outer_anderson = outer_anderson
        self.max_iter = max_iter
        self.tol = tol
        self.warm_start = warm_start
        self.inner_tol = inner_tol

    def fit(self, S):
        p = S.shape[-1]
        indices = np.arange(p)

        if self.weights is None:
            Weights = np.ones((p, p))
        else:
            Weights = self.weights
            if not np.allclose(Weights, Weights.T):
                raise ValueError("Weights should be symmetric.")

        if self.warm_start and hasattr(self, "precision_"):
            if self.algo == "dual":
                raise ValueError(
                    "dual does not support warm start for now.")
            Theta = self.precision_
            W = self.covariance_

        else:
            W = S.copy()
            W *= 0.95
            diagonal = S.flat[:: p + 1]
            W.flat[:: p + 1] = diagonal
            # Theta = np.linalg.pinv(W, hermitian=True)
            Theta = scipy.linalg.pinvh(W)

        W_11 = np.copy(W[1:, 1:], order="C")
        eps = np.finfo(np.float64).eps
        for it in range(self.max_iter):
            # Theta_old = Theta.copy()
            if self.outer_anderson:
                K = 4
                buffer_filler = 0
                anderson_mem = np.zeros(
                    (Theta.shape[0], Theta.shape[0], K+1))  # p x (p-1) x (K+1)

            for col in range(p):
                if col > 0:
                    di = col - 1
                    W_11[di] = W[di][indices != col]
                    W_11[:, di] = W[:, di][indices != col]
                else:
                    W_11[:] = W[1:, 1:]

                s_12 = S[col, indices != col]

                # penalty.weights = Weights[_12]
                if self.algo == "dual":
                    # w_init = (Theta[indices != col, col] /
                    #           (Theta[col, col] + 1000 * eps))
                    # Xw_init = W_11 @ w_init
                    Q = W_11

                elif self.algo == "primal":
                    inv_Theta_11 = (W_11 -
                                    np.outer(W[indices != col, col],
                                             W[indices != col, col])/W[col, col])
                    Q = inv_Theta_11
                    # w_init = Theta[_12] * w_22
                    # Xw_init = inv_Theta_11 @ w_init
                else:
                    raise ValueError(f"Unsupported algo {self.algo}")

                beta = (Theta[indices != col, col]
                        / (Theta[col, col] + 1000*eps))

                beta = cd_gram(
                    W_11,
                    s_12,
                    x=beta,
                    alpha=self.alpha,
                    anderson=self.inner_anderson,
                    anderson_buffer=4,
                    tol=self.inner_tol,
                    max_iter=self.max_iter,
                )

                if self.algo == "dual":
                    # Theta[col, col] = 1 / \
                    #     (W[col, col] + np.dot(beta, w_12))

                    # w_12 = -W_11 @ beta
                    w_12 = -np.dot(W_11, beta)
                    W[col, indices != col] = w_12
                    W[indices != col, col] = w_12

                    Theta[col, col] = 1 / \
                        (W[col, col] + np.dot(beta, w_12))
                    Theta[indices != col, col] = beta*Theta[col, col]
                    Theta[col, indices != col] = beta*Theta[col, col]

                # else:  # primal
                #     theta_12 = beta / s_22
                #     theta_22 = 1/s_22 + theta_12 @ inv_Theta_11 @ theta_12

                #     Theta[_12] = theta_12
                #     Theta[_21] = theta_12
                #     Theta[_22] = theta_22

                #     w_22 = 1/(theta_22 - theta_12 @ inv_Theta_11 @ theta_12)
                #     w_12 = -w_22*inv_Theta_11 @ theta_12
                #     W_11 = inv_Theta_11 + np.outer(w_12, w_12)/w_22
                #     W[_11] = W_11
                #     W[_12] = w_12
                #     W[_21] = w_12
                #     W[_22] = w_22

            if self.outer_anderson:
                if buffer_filler <= K:
                    anderson_mem[:, :, buffer_filler] = W
                    buffer_filler += 1
                else:
                    try:
                        U = np.diff(anderson_mem)
                        c = np.linalg.solve(np.dot(U.T, U), np.ones(K))
                        C = c / np.sum(c)
                        W = np.dot(np.ascontiguousarray(
                            anderson_mem[:, :, 1:]), C)
                        buffer_filler = 0
                    except np.linalg.LinAlgError:
                        print(f"linalg err at iter {it}")
                        pass

            # if norm(Theta - Theta_old) < self.tol:
            #     print(f"Weighted Glasso converged at CD epoch {it + 1}")
            #     break
        # else:
        #     print(
                # f"Not converged at epoch {it + 1}, "
                # f"diff={norm(Theta - Theta_old):.2e}"
        #     )
        self.precision_, self.covariance_ = Theta, W
        # self.n_iter_ = it + 1

        return self

# @njit
# def ST(x, tau):
#     if x > tau:
#         return x-tau
#     elif x < -tau:
#         return x + tau
#     else:
#         return 0


@njit
def ST(x, tau):
    return np.sign(x) * np.maximum(np.abs(x) - tau, 0)


@njit
def cd_gram(H, q, x, alpha, anderson=False, anderson_buffer=0, max_iter=100, tol=1e-4):
    """
    Solve min .5 * x.T H x + q.T @ x + alpha * norm(x, 1) with(out) extrapolation.

    H must be symmetric.
    """
    if anderson == True:
        K = anderson_buffer
        buffer_filler = 0
        anderson_mem = np.zeros((x.shape[0], K+1))

    dim = H.shape[0]
    lc = np.zeros(dim)
    for j in range(dim):
        lc[j] = H[j, j]

    # Hx = H @ x
    Hx = np.dot(H, x)
    for epoch in range(max_iter):
        max_delta = 0  # max coeff change

        for j in range(dim):
            x_j_prev = x[j]
            x[j] = ST(x[j] - (Hx[j] + q[j]) / lc[j], alpha/lc[j])
            max_delta = max(max_delta, np.abs(x_j_prev - x[j]))

            if x_j_prev != x[j]:
                Hx += (x[j] - x_j_prev) * H[j]
        # if max_delta <= tol:
        #     break

        if anderson:
            if buffer_filler <= K:
                anderson_mem[:, buffer_filler] = x
                buffer_filler += 1

            else:
                try:
                    U = np.diff(anderson_mem)
                    c = np.linalg.solve(np.dot(U.T, U), np.ones(K))
                    C = c / np.sum(c)
                    x = np.dot(np.ascontiguousarray(anderson_mem[:, 1:]), C)
                    buffer_filler = 0
                except:
                    # print(f"no accel at epoch {epoch}")
                    buffer_filler = 0
    return x
