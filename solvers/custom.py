from benchopt import BaseSolver, safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np

    from benchmark_utils import GraphicalLasso


class Solver(BaseSolver):

    name = 'Custom'

    parameters = {
        'algo': ["mazumder"],
    }

    requirements = ["numpy"]

    def set_objective(self, S, alpha):
        self.S = S
        self.alpha = alpha

        self.tol = 0.
        self.model = GraphicalLasso(alpha=self.alpha,
                                    algo=self.algo,
                                    warm_start=True,
                                    tol=self.tol)

    def run(self, n_iter):

        self.model.max_iter = n_iter
        self.model.fit(self.S)

        self.Theta = self.model.precision_

    def get_result(self):
        return dict(Theta=self.Theta)
