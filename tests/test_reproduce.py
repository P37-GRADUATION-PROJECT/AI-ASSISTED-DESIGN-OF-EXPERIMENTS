from scripts.reproduce import main


def test_lists_experiments():
    assert main([]) == 0


def test_unknown_experiment_fails():
    assert main(["nope"]) == 1
