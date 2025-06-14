
A Graphical Lasso Benchmark
=====================
|Build Status| |Python 3.6+|

Benchopt is a package to simplify and make more transparent and
reproducible comparisons of optimization methods.
This benchmark is dedicated to solvers of the Graphical Lasso estimator (Banerjee et al., 2008):


$$\\min_{\\Theta \\succ 0} - \\log \\det (\\Theta) + \\langle \\Theta, S \\rangle + \\alpha \\Vert \\Theta \\Vert_{1,\\mathrm{off}},$$

where $\\Theta$ is the optimization variable, $S$ is the empirical covariance matrix and $\\alpha$ is the regularization hyperparameter.

Install
--------

This benchmark can be run using the following commands, which first create a dedicated Conda environment:

.. code-block::

   $ conda create -n glasso_bench_env python=3.10
   $ conda activate glasso_bench_env
   $ pip install -U benchopt
   $ git clone https://github.com/Perceptronium/benchmark_graphical_lasso
   $ pip install gglasso
   $ git clone https://github.com/skggm/skggm ./benchmark_graphical_lasso/benchmark_utils/skggm
   $ pip install Cython
   $ pip install -e ./benchmark_graphical_lasso/benchmark_utils/skggm/
   $ benchopt run ./benchmark_graphical_lasso --config ./benchmark_graphical_lasso/simple_conf.yml


Please visit https://benchopt.github.io/ for more details on using the `benchopt` ecosystem.

.. image:: bench_fig.jpg
   :width: 350
   :align: center

.. |Build Status| image:: https://github.com/Perceptronium/benchmark_graphical_lasso/actoiworkflows/main.yml/badge.svg
   :target: https://github.com/Perceptronium/benchmark_graphical_lasso/actions
.. |Python 3.6+| image:: https://img.shields.io/badge/python-3.6%2B-blue
   :target: https://www.python.org/downloads/release/python-360/
