from databoom.generation import SeedManager


def test_seed_manager_derives_repeatable_child_seeds() -> None:
    first = SeedManager(42)
    second = SeedManager(42)

    assert first.child_seed("users", "email") == second.child_seed("users", "email")


def test_seed_manager_namespaces_streams() -> None:
    manager = SeedManager(42)

    assert manager.child_seed("users") != manager.child_seed("orders")


def test_seed_manager_streams_are_repeatable_and_isolated() -> None:
    first = SeedManager("demo").stream("users", "email")
    second = SeedManager("demo").stream("users", "email")
    other = SeedManager("demo").stream("users", "name")

    assert [first.randint(1, 100) for _ in range(5)] == [
        second.randint(1, 100) for _ in range(5)
    ]
    assert [first.randint(1, 100) for _ in range(5)] != [
        other.randint(1, 100) for _ in range(5)
    ]
