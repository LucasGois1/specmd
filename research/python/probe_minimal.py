"""Small real-engine probe. Requires the pinned packages in requirements.in."""

import json

from behave.configuration import Configuration
from behave.parser import parse_feature
from behave.runner import ModelRunner
from behave.step_registry import StepRegistry


def add(a, b):
    return a + b


def operands(context, a, b):
    context.operands = (a, b)


def calculate(context):
    context.result = add(*context.operands)


def check_result(context, expected):
    assert context.result == expected, (context.result, expected)


def run_case(name, expected):
    text = f"""# language: pt
Funcionalidade: Soma em memória
  Cenário: {name}
    Dado os números 2 e 3
    Quando a soma for calculada
    Então o resultado deve ser {expected}
"""
    feature = parse_feature(text, filename="probe.md")
    registry = StepRegistry()
    registry.add_step_definition("given", "os números {a:d} e {b:d}", operands)
    registry.add_step_definition("when", "a soma for calculada", calculate)
    registry.add_step_definition("then", "o resultado deve ser {expected:d}", check_result)
    config = Configuration([], load_config=False)
    config.reporters = []
    runner = ModelRunner(config, features=[feature], step_registry=registry)
    engine_failed = runner.run_model()
    return {
        "case": name,
        "engine_failed": engine_failed,
        "scenarios": [
            {"name": scenario.name, "status": scenario.status.name}
            for scenario in feature.scenarios
        ],
    }


if __name__ == "__main__":
    results = [run_case("positive", 5), run_case("assertion_failure", 99)]
    print(json.dumps(results, ensure_ascii=False, indent=2))
