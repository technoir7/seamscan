"""Secret-shaped test values, built by concatenation (spec §8.1).

Case files contain only placeholders like {{FAKE_STRIPE_LIVE}}. Keeping the
literal shapes out of the repo stops GitHub push protection and secret
scanning from flagging the benchmark. None of these values is a real credential.
"""

FAKES: dict[str, str] = {
    "FAKE_STRIPE_LIVE": "sk_" + "live_" + "51HxQ2aZ8kL9mN3pQ7rT5vW1yB4cE6gJ0aB2cD4eF6gH8iJ0kL2mN4",
    "FAKE_STRIPE_PK_LIVE": "pk_"
    + "live_"
    + "51HxQ2aZ8kL9mN3pQ7rT5vW1yB4cE6gJ0aB2cD4eF6gH8iJ0kL2mN4",
    "FAKE_STRIPE_TEST": "sk_" + "test_" + "51HxQ2aZ8kL9mN3pQ7rT5vW1yB4cE6gJ0aB2cD4eF6gH8iJ0kL2mN4",
    "FAKE_OPENAI_PROJ": "sk-" + "proj-" + "Qm7Rk2Lp9Xv4Tn8Bw3Jc6Hd1Fs5Gy0Ae7Uz2Wq4Ri9Ot3Pm6Sl8Kn1",
    "FAKE_GITHUB_PAT": "ghp" + "_" + "R7kL2mQ9xV4tN8bW3jC6hD1fS5gY0aE7uZ2w",
    "FAKE_AWS_KEY_ID": "AKIA" + "Z7QX3M2KLP9RTV4N",
}
