#  Copyright (c) 2023. Fraunhofer-Gesellschaft zur Foerderung der angewandten Forschung e.V.
#  acting on behalf of its Fraunhofer-Institut für Kognitive Systeme IKS. All rights reserved.
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see <http://www.gnu.org/licenses/>.
#
#  https://www.gnu.de/documents/gpl-2.0.de.html
#
#  Contact: alireza.zamanian@iks.fraunhofer.de
import numpy as np
import os
import pytest
from parcs.graph_builder.parsers import *
from parcs.exceptions import *


class TestTermParser:
    """
    Term parser parses the individual terms in an equation such as 2XY, -0.5Z, etc.
    """

    @staticmethod
    @pytest.mark.parametrize('term,vars,exp_pars,exp_coef', [
        # bias terms
        ('0', ['A', 'B', 'Z_1'], [], 0),
        ('1.5', ['A', 'B', 'Z_1'], [], 1.5),
        ('3', ['A', 'B', 'Z_1'], [], 3),
        ('-0', ['A', 'B', 'Z_1'], [], 0),
        ('-0.6', ['A', 'B', 'Z_1'], [], -0.6),
        ('-2', ['A', 'B', 'Z_1'], [], -2),
        # linear terms
        ('B', ['A', 'B', 'Z_1'], ['B'], 1),
        ('-0.3Z_1', ['A', 'B', 'Z_1'], ['Z_1'], -0.3),
        ('1.7A', ['A', 'B', 'Z_1'], ['A'], 1.7),
        # interaction terms
        ('ABZ_1', ['A', 'B', 'Z_1'], ['A', 'B', 'Z_1'], 1),
        ('2Z_1A', ['A', 'B', 'Z_1'], ['A', 'Z_1'], 2),
        ('-0.3BA', ['A', 'B', 'Z_1'], ['A', 'B'], -0.3),
        # quadratic terms
        ('A^2', ['A', 'B', 'Z_1'], ['A', 'A'], 1),
        ('1.6Z_1^2', ['A', 'B', 'Z_1'], ['Z_1', 'Z_1'], 1.6),
        ('-3B^2', ['A', 'B', 'Z_1'], ['B', 'B'], -3)
    ])
    def test_parse_terms_correctly(term, vars, exp_pars, exp_coef):
        """
        Tests whether the outputs are correct when inputs are correct.

        The test parameters:
            - term: the string term which the function receives
            - vars: the list of possible parents that the function must look for
            - exp_pars: first output - expected present parents in the term
            - exp_coef: second output - expected multiplicative factor of the term
        """
        pars, coef = term_parser(term, vars)
        assert sorted(pars) == sorted(exp_pars)
        assert coef == exp_coef

    @staticmethod
    @pytest.mark.parametrize('term,vars,err', [
        # bias terms
        ('J', ['A', 'B', 'Z_1'], DescriptionFileError),  # not existing parent
        ('AZ_1A', ['A', 'B', 'Z_1'], DescriptionFileError),  # parent duplicate
        ('AA', ['A', 'B', 'Z_1'], DescriptionFileError),  # parent duplicate
        ('2B^2A', ['A', 'B', 'Z_1'], DescriptionFileError),  # invalid quadratic term
        ('2AB^2', ['A', 'B', 'Z_1'], DescriptionFileError),  # invalid quadratic term
        ('2B^3', ['A', 'B', 'Z_1'], DescriptionFileError)  # invalid power
    ])
    def test_parse_terms_raise_correct_error(term, vars, err):
        """
        Tests whether an error is raised in case of invalid inputs.

        The test parameters:
            - term: the string term which the function receives
            - vars: the list of possible parents that the function must look for
            - err: the error it must return
        """
        with pytest.raises(err):
            term_parser(term, vars)


class TestEquationParser:
    """
    This parser parses equations which are made of terms, e.g. '2X + 3Y - X^2 + 1'
    """

    @staticmethod
    @pytest.mark.parametrize('eq,vars,output', [
        ('2+A-2.8B', ['A', 'B'], [([], 2), (['A'], 1.0), (['B'], -2.8)]),  # example equation, no space
        ('1', ['A', 'B'], [([], 1)]),  # only bias
        ('A^2-2AB', ['A', 'B'], [(['A', 'A'], 1), (['A', 'B'], -2.0)])  # quadratic terms with space
    ])
    def test_parse_equations(eq, vars, output):
        """
        Tests whether the outputs are correct when inputs are correct.

        The test parameters:
            - eq: the string term which the function receives
            - vars: the list of possible parents that the function must look for
            - output: the parsed equation
        """
        terms = equation_parser(eq, vars)
        for gen, correct in zip(sorted(terms), sorted(output)):
            assert set(gen[0]) == set(correct[0])  # parents are correct
            assert gen[1] == correct[1]  # coefficient is correct

    @staticmethod
    @pytest.mark.parametrize('eq,vars,err', [
        # duplicate terms
        ('2A + 3A', ['A', 'B'], DescriptionFileError),
        ('2AB + 3BA', ['A', 'B'], DescriptionFileError),
        ('B + 2A^2 - A^2', ['A', 'B'], DescriptionFileError),
        # non-existing parents
        ('B + 2A^2', ['B'], DescriptionFileError),
        # non-standard symbols
        ('A + B * 3', ['B'], DescriptionFileError),

    ])
    def test_parse_equations_raise_error(eq, vars, err):
        """
        Tests whether an error is raised in case of invalid inputs.

        The test parameters:
            - term: the string term which the function receives
            - vars: the list of possible parents that the function must look for
            - the error it must return
        """
        with pytest.raises(err):
            equation_parser(eq, vars)


class TestNodeParser:
    """
    This parser parses lines of description files to give config dicts for nodes.
    """
    @staticmethod
    @pytest.mark.parametrize('line,parents,dict_output', [
        ('constant(2)', ['A', 'B'], {'value': 2}),
        ('constant(-0.3)', ['A', 'B'], {'value': -0.3}),
        ('constant(0)', ['A', 'B'], {'value': 0}),
    ])
    def test_parse_constant_node(line, parents, dict_output):
        assert node_parser(line, parents) == dict_output

    @staticmethod
    @pytest.mark.parametrize('line,parents', [
        ('constant(A)', ['A', 'B']),
        ('constant()', ['A', 'B']),
    ])
    def test_parse_constant_node_raise_error(line, parents):
        with pytest.raises(DescriptionFileError):
            node_parser(line, parents)

    @staticmethod
    @pytest.mark.parametrize('line,parents,dist,param_coefs,do_correction,correction_config', [
        ('bernoulli(p_=2A+B^2)', ['A', 'B'], 'bernoulli',
         {'p_': {'bias': 0, 'linear': [2, 0], 'interactions': [0, 0, 1]}}, False, {}),
        ('gaussian(mu_=1-0.3AB, sigma_=2)', ['A', 'B'], 'gaussian',
         {'mu_': {'bias': 1, 'linear': [0, 0], 'interactions': [0, -0.3, 0]},
          'sigma_': {'bias': 2, 'linear': [0, 0], 'interactions': [0, 0, 0]}}, False, {}),
        ('uniform(mu_=4B, diff_=A^2)', ['A', 'B'], 'uniform',
         {'mu_': {'bias': 0, 'linear': [0, 4], 'interactions': [0, 0, 0]},
          'diff_': {'bias': 0, 'linear': [0, 0], 'interactions': [1, 0, 0]}}, False, {}),
        ('lognormal(mu_=A+B, sigma_=A)', ['A', 'B'], 'lognormal',
         {'mu_': {'bias': 0, 'linear': [1, 1], 'interactions': [0, 0, 0]},
          'sigma_': {'bias': 0, 'linear': [1, 0], 'interactions': [0, 0, 0]}}, False, {}),
        ('poisson(lambda_=B^2+1)', ['A', 'B'], 'poisson',
         {'lambda_': {'bias': 1, 'linear': [0, 0], 'interactions': [0, 0, 1]}}, False, {}),
        ('exponential(lambda_=-AB)', ['A', 'B'], 'exponential',
         {'lambda_': {'bias': 0, 'linear': [0, 0], 'interactions': [0, -1, 0]}}, False, {}),
        # parentless nodes: only test one distribution since logic is the same
        ('bernoulli(p_=2)', [], 'bernoulli',
         {'p_': {'bias': 2, 'linear': [], 'interactions': []}}, False, {}),
    ])
    def test_parse_stochastic_node(line, parents, dist, param_coefs, do_correction, correction_config):
        out = node_parser(line, parents)
        # distribution
        assert out['output_distribution'] == dist
        # params
        assert set(out['dist_params_coefs'].keys()) == set(param_coefs.keys())
        # coefs
        for param in out['dist_params_coefs'].keys():
            for coef_type in ['bias', 'linear', 'interactions']:
                assert np.array_equal(out['dist_params_coefs'][param][coef_type], param_coefs[param][coef_type])
        # correction
        assert out['do_correction'] == do_correction
        assert out['correction_config'] == correction_config

    @staticmethod
    @pytest.mark.parametrize('line,parents', [
        ('fakedist(p_=2A+B^2)', ['A', 'B']),  # wrong distribution name
        ('bernoulli(mu_=2A+B^2)', ['A', 'B']),  # wrong parameter name
        ('gaussian(mu_=2A+B^2, mu_=2, sigma_=3)', ['A', 'B']),  # duplicate params
        ('exponential(lambda_=2A+B^2)', []),  # wrong parents
        ('poisson(lambda_=B^2)', ['A'])  # wrong parents
    ])
    def test_parse_stochastic_node_raises_error(line, parents):
        with pytest.raises(DescriptionFileError):
            node_parser(line, parents)

    @staticmethod
    @pytest.fixture(scope='class')
    def write_custom_function_py():
        # setup
        with open('./customs.py', 'w') as script:
            script.write("def custom_function(data): return data['A'] + data['B']")
        # test
        yield True
        # teardown
        os.remove('./customs.py')

    @staticmethod
    def test_parse_deterministic_node(write_custom_function_py):
        out = node_parser('deterministic(customs.py, custom_function)', ['A', 'B'])
        assert 'function' in out.keys()
        assert out['function'].__name__ == 'custom_function'

    @staticmethod
    def test_parse_deterministic_node_raises_error(write_custom_function_py):
        with pytest.raises(ExternalResourceError):
            node_parser('deterministic(non_existing.py, custom_function)', ['A', 'B'])
        with pytest.raises(ExternalResourceError):
            node_parser('deterministic(customs.py, non_existing_function)', ['A', 'B'])

    @staticmethod
    def test_parse_data_node():
        out = node_parser('data(./some_data.csv)', [])
        assert out == {'csv_dir': './some_data.csv'}

    @staticmethod
    def test_parse_data_node_raise_error():
        with pytest.raises(DescriptionFileError):
            node_parser('data(./some_data.csv)', ['A'])

    @staticmethod
    def test_parse_random_stochastic_node():
        out = node_parser('random', ['A', 'B'])
        assert out == {'output_distribution': '?', 'do_correction': True}
